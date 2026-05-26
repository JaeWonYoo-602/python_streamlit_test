import streamlit as st

#streamlit run 파일이름.py
#타이틀 텍스트
st.title('테스트 웹 앱')
st.write('# :smile: :sunglasses: :cry:')
st.write('# 제목')
st.write('### 부제목')
st.write('##### 소제목')
'그냥 문자열 작성'
'''
# 여러줄 문자 제목
#### 여러줄 문자 부제목
문자열 줄바꿈 하려면 스페이스바 두번  
이렇게  
#### 지금부터 코드
```python
import streamlit as st

a=3
b=4
print(a+b)
```

## 마크다운 작성법
- 번호없는 목록
- *이탈릭*
- **볼드**
1. 번호있는 목록  
    1.하위 목록1  
    1.하위 목록2
1. :blue[번호있는 목록]
1. :red[번호있는 목록]  
[링크 첨부하기](www.google.com)
'''


st.divider()

with st.echo():
    name='Jammy'
    st.write(name)

123456

st.caption('캡션')

'## 데이터 프레임'
import pandas as pd
df = pd.DataFrame(
    {'id':[1,2,3],
     'name':['A', 'B', 'C'],
     'age':[24,35,32]
    }
)
df  

st.image('C:/Users/dbwod/Desktop/pypy/data/xxxdd.jpg')

'## 마크다운에서의 테이블'
'''
|이름|학번|
|---|---|
|A|123456|
|B|789456|
'''
#
