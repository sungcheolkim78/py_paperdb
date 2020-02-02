# py_paperdb

여러 논문을 읽고 관리하는 일은 연구를 하는 모든 사람이 부딪히게 되는 문제이다. 모두가 각각의 방법을 가지고 있고 어느 것이 가장 효율적인지는 말할 수 없다. 나도 많은 시간동안 논문 정리를 여러가지 방법으로 해 보았고 각각의 방법에는 모두 각각의 문제점을 가지고 있다. 그동안 이용한 가장 대표적인 방법은 특정 프로그램을 이용하고 각각의 프로그램들이 제공하는 기능들을 충실히 따르는 것이었다. 가장 많이 사용했던 프로그램은 papers 였는데, 최근 버전을 보니 여러가지 기능들이 사라져 버렸고 출판사의 제제를 받은 것처럼 보여 사용하기가 불편하였다. 그러던 중 파이썬을 이용해서 내가 필요로 하는 작업들을 자동화하고 또한 기계 학습을 도입하여 논문을 읽고 정리해보고자 관련 라이브러리를 만들게 되었다. Andrew Kapathy의 arXiv 정리 논문 사이트가 많은 영감을 주었다. 

## 버전들 

- version 1.0 - 2019/04/01 - stage 1 - initial concept
- version 1.1 - 2019/04/15 - stage 2 - new concept
- version 1.2 - 2020/02/01 - stage 3 - documentation

## Install

필요한 라이브러리들은 다음과 같다. 

- pandas 
- numpy
- bibtexparser
- requests
- arxiv2bib
- py_readpaper 

github에서 리퍼지토리(repository)를 클론(clone)한 후에 해당 디렉토리로 들어가서 pip3을 이용하여 설치한다. 필요한 라이브러리들을 함께 설치할 것이다. 현재는 파이썬3 버전에서만 실행 가능한지 확인하였다. 

```
pip3 install -e .
```

## Usage

### Initial Concepts

특정 주제에 관해 지식을 쌓기 위해서는 관련된 많은 논문을 읽어야 한다. 연구는 각 단계에 따라 검색, 다운로드, 정리, 읽기, 개인 정리, 논문 찾기, 서지 정보 출력의 작업이 반복되는 일이다. 이를 구체적으로 다음과 같이 나누어 보았다. 

- `관심있는 논문 검색 및 다운로드`: 이는 학교의 계정을 이용하거나 회사가 제공하는 저널의 논문을 다운받거나 무료로 제공하는 pdf 파일을 구하는 것이다. 여러가지 방법이 있으나 이 라이브러리에서는 어떤 방식으로든 구해진 pdf 파일로부터 작업을 시작한다.
- `서지 정보 찾기 및 메타(meta) 정보 입력하기`: 이 라이브러리에서는 crossref.org의 API를 사용하여 제목으로부터 혹은 DOI으로부터 bibtex과 호환되는 정보를 찾아내고 이를 각 파일에 해당하는 숨겨진 파일(hidden file)을 만들어서 저장한다. 이는 두가지 단계로 진행된다.
  - 첫번째는 tmp-paper 폴더에 다운받은 파일을 모두 모아놓고 최대한 자동적으로 서지 정보를 찾아내고 이를 `년도-저자명-저널.pdf` 형식의 이름으로 저장한다. 또한 pdf 파일에 최대한 meta 정보를 입력하여 다시 저장한다. 
  - 두번째는 처리가 끝난 논문들을 paper 폴더에 저장하고 자동적으로 찾아내지 못한 정보들을 jupyter notebook을 통해 상호 반응적(interactive)으로 서지 정보를 입력한다. 
- `관심 논문 찾기 및 읽기`: 이렇게 모여진 논문들을 읽고 또한 저자별로 혹은 주제별로 혹은 기계학습에 따른 유사성등으로 검색한다. 
- `특정 주제에 대한 논문들 서지 정보 출력하기`: 대부분 논문 읽기의 마지막 단계는 쓰고자 하는 논문의 참조 문헌 목록을 작성하기 위함일 것이다. 이를 위해서 검색된 논문들의 리스트를 작성하고 필요한 논문들을 추가/삭제한 후 이를 bibtex 형식으로 출력한다. 

### [step 1] Tag meta data to downloaded papers

1. 논문을 `YEAR-LAST NAME OF FIRST AUTHOR-JOURNAL.pdf` 의 이름으로 저장한다. 이는 기억하기 쉽고 사람들과 대화할 때에도 보통 "몇년도 누가 쓴 논문이다"라고 말하기에 이를 따른 것이다. 그러나 실제적으로는 BibDesk에서 처럼 citekey로 저장하는 것이 유일한 색인을 가능하게 하여 관리가 편하다.
1. 가능하면 관련 citation 파일을 다운받아 같은 폴더에 저장한다. 보통 bibtex 파일을 사용하는데, 파일 이름은 중요하지 않다.

```
$ ./proc_newfiles.py
```

### [step 2] Maintain paper database

2009년도에 나온 논문들 중에 우선 bib 파일을 없는 것들의 숫자를 보여준다. 그리고 나서 각각의 파일에 대해 우선 EXIF 정보를 통해 doi, title, year, author등의 정보를 알아낸다. 그리고 부족한 정보들은 doi를 통해 다운로드 받거나 title을 통해 검색하거나 기존의 bibtex database로부터 찾아낼 수 있다. 이를 통해 bib 정보를 갱신하고 이후에 다시 이 정보를 가지고 EXIF 정보를 업데이트 한다. 각각의 파일은 pdf와 bib 파일을 갖게 된다.

대부분의 파일들을
1. bib citation 파일들을 가지고 있거나 (이 경우 초기 값이 거의 없다.)
1. title를 통해 doi를 찾을 수 있거나 (주로 따로 title을 입력해야 한다.)
1. doi를 알때 관련 서지 정보를 찾을 수 있다. (다른 정보들이 있어도 다시 한번 crossref를 통해 정보를 갱신한다.)
의 세가지 경우를 통해서 meta 정보를 찾고 EXIF 정보를 업데이트 할 수 있다.

```python
import py_paperdb
py_paperdb.check_files(globpattern="2009-*.pdf", count=True)
py_paperdb.check_files(globpattern="2009-*.pdf")
```

### [step 2] Search papers and export metadata as bibtex

```python
import py_paperdb
p = py_paperdb.PaperDB()
p.search_sep(author1='Kim')
```
