# py_paperdb

## Concepts

연구를 위해서는 많은 논문을 보고 정리해야 한다. 이는 주로 검색, 다운로드, 읽기, 정리의 순서로 일어나게 된다. 이전에는 papers 라는 프로그램으로 논문들을 관리 했었는데, 1500개 이상으로 논문이 늘어 나면서 관리하는 것이 쉽지 않아 져서 machine learning을 이용해서 논문 관리를 할 수 없을까 고민하게 되었다. 그러한 목적을 가지고 우선 기본적으로 필요한 python library를 만들어 보았다.

작업 순서는 다음과 같다.

1. 논문을 `YEAR-LAST NAME OF FIRST AUTHOR-JOURNAL.pdf` 의 이름으로 저장한다. 이는 기억하기 쉽고 사람들과 대화할 때에도 보통 "몇년도 누가 쓴 논문이다"라고 말하기에 이를 따른 것이다. 그러나 실제적으로는 BibDesk에서 처럼 citekey로 저장하는 것이 유일한 색인을 가능하게 하여 관리가 편하다.
1. 가능하면 관련 citation 파일을 다운받아 같은 폴더에 저장한다. 보통 bibtex 파일을 사용하는데, 파일 이름은 중요하지 않다.
1. `master_db.bib`에 모든 pdf 파일의 관련 정보를 저장하였다. 이 파일은 `BibDesk`를 사용하여 논문을 찾고 GUI 기반의 작업을 가능하게 한다.
1. 동시에 `master_db.csv`파일에 서지 정보를 `comma-separated values`로 저장하였다. `panda` 패키지로 손쉽게 관리할 수 있고 아무 text editor로도 편집할 수 있다. 처음에는 bib file이 중심이 되지만, 나중에는 csv 파일이 주가 되고 이 파일에서 bib file를 선택적으로 생성할 것이다. 예를 들어 특정 논문을 작성하기 위해 필요한 서지 정보를 모으고 이를 별도의 bib file로 출력하여 논문 정리 폴더에 넣어 두는 식이다.
1. 논문 파일 정리과 서지 정보 정리가 끝나면 필요한 논문을 찾아 내는 일은 기본적인 검색 방법을 사용하거나 머신 러닝 알고리즘을 사용할 수 있다. recommender system를 구축할 것이다.
1. [ ] 새로운 논문을 추가하거나 빼내는 작업을 한다.

## Quick start

```python
import py_paperdb
p = py_paperdb.read_paperdb(FILENAME)
py_paperdb.search(p, year=2010, author='Kim')
```

## pdf file Management

우선 파일명에서 `year`, `author_s`, `journal`의 정보를 알아낼 수 있다. (이는 수동으로 해야 한다.) `pdftotext`나 `pdfminer`를 사용해서 pdf에서 텍스트를 추출할 수 있는데, pdf 파일 자체가 글을 적는 용도가 아니라 그림을 저장하는 용도에 가까운 포맷이라 거기서 따로 서지정보를 알아내기가 쉽지 않다.

- [ ] pdf 파일로부터 논문의 title을 뽑아내자. 자동으로 모든 것을 할 수 없다면 몇가지 옵션으로 추려내고 선택을 사용자에게 맡기자.
- [ ] pdf 파일로부터 keyword를 자동으로 생성하자. gensim을 통해서 자연어 처리 알고리즘으로 abstract나 모든 본문에서 keyword를 생성할 수 있다.
- [ ] 기존 정보 (year, author, journal)을 본문을 통해 확인할 수 있다.
- [ ] pdf 파일을 metadata를 업데이트 한다.

## bibtex file Management

기본적으로 python dictionary 형태의 정보를 가지고 있으면 Bibtexparser 패키지로 쉽게 pandas DataFrame과 csv, bib 간의 변환이 가능하다. master file을 가지고 있거나 csv 파일을 기본으로 하고 내용이 정확한지 확인하거나 모자란 정보를 채우는데 도움이 되는 함수들을 만든다.

- [ ] 여러개의 bibtex 아이템들 중에 가장 정보를 많이 가지고 있는 것으로 merge하고 duplicated items을 분별한다.
- [ ] pdf 파일 정보로 부터 실제 파일과 `local-url`로 연결 시킨다.

### Examples

```python
file_db = py_paper.build_pd(DIR)
bib_db = py_paper.read_bib(FILENAME)
```

