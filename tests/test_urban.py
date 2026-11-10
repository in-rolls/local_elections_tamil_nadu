import gzip
import hashlib

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from local_elections_tamil_nadu.parse import urban


def test_complete_build_preserves_sources_and_unknown_sex(tmp_path):
    urban.build(tmp_path)
    candidates = pq.read_table(tmp_path / "candidates.parquet")
    winners = pq.read_table(tmp_path / "winners.parquet")
    assert candidates.num_rows == 5920
    assert winners.num_rows == 500
    assert winners.equals(pq.read_table(urban.OUT / "winners.parquet"))
    rows = winners.to_pylist()
    earlier = [r for r in rows if r["year"] == 2011]
    assert len(earlier) == 200
    assert all(
        r["winner_woman"] is None and r["reserved_woman"] is None for r in earlier
    )
    assert not any(r["is_geographic_link_validated"] for r in rows)
    conflicts = pq.read_table(
        tmp_path / "reserved_source_conflicts.parquet"
    ).to_pylist()
    assert {r["ward_no"] for r in conflicts} == {"183", "185"}
    chennai = [r for r in rows if r["year"] == 2022 and r["body"] == "Chennai"]
    assert sum(r["reserved_woman"] for r in chennai) == 100
    assert sum(r["winner_woman"] for r in chennai) == 101
    assert all(
        r["reserved_basis"] == "official_january_17_2022_gazette" for r in chennai
    )
    assert all(r["winner_woman"] for r in chennai if r["reserved_woman"])
    coimbatore = [r for r in rows if r["body"] == "Coimbatore"]
    assert len(coimbatore) == 100
    assert all(r["reserved_source_conflict"] is None for r in coimbatore)
    assert all(r["councilor_name_raw"] for r in coimbatore)
    assert {r["ward_no"] for r in coimbatore} == {str(n) for n in range(1, 101)}
    gender = [
        r for r in candidates.to_pylist() if r["candidate_woman_raw"] == "Transgender"
    ]
    assert len(gender) == 3
    assert all(r["candidate_woman"] is None for r in gender)


def test_primary_gazette_and_councilor_rows():
    roster = urban.chennai_reservations(urban.RAW / "chennai_reservation_2022.pdf")
    assert roster["183"]["reserved_woman"] and roster["185"]["reserved_woman"]
    assert roster["183"]["source_page"] == 4
    assert roster["183"]["source_row"] == 79
    assert roster["185"]["source_row"] == 80
    councilors = urban.coimbatore_councilors(
        urban.RAW / "coimbatore_councilors_2022.pdf"
    )
    assert councilors["1"]["councilor_name_raw"] == "Karpagam R"
    assert councilors["1"]["party"] == "DMK"
    assert councilors["1"]["source_page"] == 1


def test_source_change_rejected(tmp_path, monkeypatch):
    path = tmp_path / "source.csv"
    original = b"ward,name\n1,name\n"
    path.write_bytes(original + b"\n")
    monkeypatch.setattr(urban, "ROOT", tmp_path)
    monkeypatch.setattr(urban, "SOURCES", [path.name])
    monkeypatch.setattr(
        urban,
        "logged",
        lambda: {
            path.name: {
                "sha256": hashlib.sha256(original).hexdigest(),
                "bytes": len(original),
            }
        },
    )
    with pytest.raises(ValueError, match="Source changed"):
        urban.verify_sources(tmp_path)


def test_incomplete_frame_rejected():
    rows = urban.parse_2011(urban.RAW / "chennai_candidates_2011.html.gz")
    rows = [r for r in rows if r["ward_no"] != "200"]
    with pytest.raises(ValueError, match="winner frame"):
        urban.validate_frame(rows, 200)


def test_error_page_not_results(tmp_path):
    path = tmp_path / "error.html.gz"
    path.write_bytes(gzip.compress(b"<html>Server error</html>"))
    with pytest.raises(ValueError, match="dated Chennai"):
        urban.parse_2011(path)


def test_declared_schemas_keys_and_dictionary_are_verified():
    from local_elections_tamil_nadu.build.release import OUTPUTS, checks_urban

    for name, (schema, key, count, _) in urban.TABLES.items():
        table = pq.read_table(urban.OUT / f"{name}.parquet")
        assert table.schema.equals(schema)
        assert table.num_rows == count
        assert table.schema.field("ward_no").type == pa.string()
        if "candidate_no" in table.column_names:
            assert table.schema.field("candidate_no").type == pa.string()
        for field in ["candidate_woman", "winner_woman", "reserved_woman"]:
            if field in table.column_names:
                assert table.schema.field(field).type == pa.int8()
                assert table.schema.field(field).nullable
        assert urban.contracts()["tables"][name]["primaryKey"] == key
    assert {f"release/urban/{name}" for name in urban.RELEASE_FILES}.issubset(OUTPUTS)
    assert checks_urban()[0]["status"] == "pass"


def test_schema_and_duplicate_key_rejected():
    table = pq.read_table(urban.OUT / "winners.parquet")
    with pytest.raises(ValueError, match="names, order, types or nullability"):
        urban.validate_table("winners", table.drop(["winner_woman"]))
    duplicate = pa.concat_tables([table.slice(0, 499), table.slice(0, 1)])
    with pytest.raises(ValueError, match="duplicate primary key"):
        urban.validate_table("winners", duplicate)
    index = table.schema.get_field_index("winner_woman")
    wrong_type = table.set_column(
        index,
        pa.field("winner_woman", pa.int64()),
        table["winner_woman"].cast(pa.int64()),
    )
    with pytest.raises(ValueError, match="names, order, types or nullability"):
        urban.validate_table("winners", wrong_type)


def test_null_sex_cannot_become_zero():
    table = pq.read_table(urban.OUT / "candidates.parquet")
    values = table["candidate_woman"].to_pylist()
    assert values[0] is None
    values[0] = 0
    index = table.schema.get_field_index("candidate_woman")
    changed = table.set_column(
        index, table.schema.field(index), pa.array(values, type=pa.int8())
    )
    with pytest.raises(ValueError, match="disagrees with raw cell"):
        urban.validate_table("candidates", changed)


def test_published_output_tampering_rejected(tmp_path):
    import shutil

    for name in urban.RELEASE_FILES:
        shutil.copy2(urban.OUT / name, tmp_path / name)
    path = tmp_path / "profile.json"
    path.write_text(path.read_text() + "\n")
    with pytest.raises(ValueError, match="output checksum changed"):
        urban.validate_release(tmp_path)
