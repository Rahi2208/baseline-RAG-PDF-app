import pandas as pd
import pymupdf
import pytest

from data_agent.doc_loader import classify, load_inputs, normalize_column, read_data


@pytest.mark.parametrize('raw, clean', [
    ('String Length (m)', 'string_length_m'),
    ('  Time 10 Swings (s) ', 'time_10_swings_s'),
    ('10 cm', 'c_10_cm'),
    ('%%%', 'column'),
])
def test_normalize_column(raw, clean):
    assert normalize_column(raw) == clean


def test_classify():
    assert classify('guide.PDF') == 'guide'
    assert classify('photo.jpg') == 'guide'
    assert classify('data.xlsx') == 'data'
    assert classify('virus.exe') is None


def test_read_data_duplicate_column_names(tmp_path):
    path = tmp_path / 'd.csv'
    pd.DataFrame([[1, 2]], columns=['Value', 'value ']).to_csv(path, index=False)
    sheets = read_data(str(path))
    assert list(sheets['data'].columns) == ['value', 'value_2']


def test_load_inputs_scanned_pdf_page_is_rendered(tmp_path):
    # page 1 has text, page 2 is empty (like a scan) -> page 2 becomes an image
    pdf = tmp_path / 'guide.pdf'
    doc = pymupdf.open()
    doc.new_page().insert_text((50, 72), 'Calculate the average of the value column. ' * 5)
    doc.new_page()
    doc.save(pdf)
    data = tmp_path / 'data.csv'
    pd.DataFrame({'Value': [1, 2, 3]}).to_csv(data, index=False)

    bundle = load_inputs([str(pdf)], str(data), str(tmp_path / 'job'))

    assert 'average' in bundle.guide_text
    assert len(bundle.guide_images) == 1 and bundle.guide_images[0].endswith('page2.png')
    assert bundle.sheets[0].columns == ['value'] and bundle.sheets[0].n_rows == 3
