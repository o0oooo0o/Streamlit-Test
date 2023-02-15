# -*- coding: utf-8 -*-
from tracemalloc import start
import streamlit as st
import requests
import os
import time
import numpy as np
import base64
import io
from PIL import Image


## uvicorn fastapi_server_nas:app --host=0.0.0.0 --port 7000
## htts://localhost:7000/docs
## streamlit run streamlit_front_ed1.py

# - 탐색 구간 설정하는 부분 slider가 아니더라도 V
# - 파일 리스트 길게 늘어나는거 축소 안되나
# - 영상 선택전 에러뜨는거 V
# - 일괄 적용 문구 표시
# - duration이 가장 작은 영상 위주로 slider가 나오게끔
# - 영상 모두 선택 기능 V
# - 다운로드 버튼 누르면 rerun되는거 V

# 요청받은 추가기술 리스트
# 1. 다중 영상 입력 및 처리 V
# 2. 예능의 경우 좌상단 로고 제거


REST_API_URL = os.environ.get('REST_API_URL', 'http://localhost:7000')
st.set_page_config(page_title='AI Thumbnail', layout='wide')


def ai_thumbnail_generation():
    # hide_streamlit_style = """
    #             <style>
    #             #MainMenu {visibility: hidden;}
    #             footer {visibility: hidden;}
    #             </style>
    #             """
    # st.markdown(hide_streamlit_style, unsafe_allow_html=True)
    st.title('AI Thumbnail :)')
    
    hms_to_s = [3600, 60, 1]
    start_point = '00:03:00'
    end_point = '60'
    video_genre = ''
    
    
    with st.sidebar:
        st.sidebar.header('Input Informations')    
        
        # 작업공간 path 입력
        file_path = st.text_input('video path', placeholder='ex. C://home/hs/Downloads...')
        if file_path != '':
            data = {'upload_dir': file_path}
            video_infos = requests.post(REST_API_URL+'/ai-thumbnail/show-video-files', data=data)
            video_infos = video_infos.json()
            
            file_index_list = []
            file_name_list = []
            for i in video_infos:
                file_index_list.append(i)
                file_name_list.append(video_infos[i]['fileName'])
            
            print(file_index_list)
            print(file_name_list)
            
            # path 안에 있는 영상 중 작업할 영상 선택 (중복가능)
            all_check_box = st.checkbox('ALL')
            check_boxes = [st.checkbox(stock, key=stock) for stock in file_name_list]
            
            # 가장 첫 번째 선택된 기준 영상의 인덱스 정보 읽기
            if True in check_boxes:
                index = int(np.array(file_index_list)[np.array(check_boxes)][0])
                
                # 기준 영상의 비디오 길이 정보 읽기
                data = {'index': index}
                requests.post(REST_API_URL+'/ai-thumbnail/select-video', data=data)
                res = requests.get(REST_API_URL+'/ai-thumbnail/get-video-duration')
                duration = res.json()
                duration = duration['total_duration']
                print(duration)
                
            
            if all_check_box is True:
                check_boxes = [True]*len(check_boxes)
                print('select ALL')
            
            # 장르 선택
            video_genre = st.radio("Select video genre", ("animation", "variety", "others"), horizontal=True)
            
            # 탐색 구간 시작시간 선택
            start_point = st.text_input('Select start time', value='00:03:00')
            start_point = str(sum([a*b for a,b in zip(hms_to_s, map(int,start_point.split(':')))]))
            
            # 탐색 구간 종료시간 선택
            end_point = st.radio('Select duration', ('1 min', '3 min', '5 min', '10 min'), horizontal=True)
            end_point = str(int(start_point) + 60*int(end_point.split(' ')[0]))
            
            # appointment = st.slider('썸네일 탐색 구간', time(0,0), time(23,0), value=(time(11, 30), time(12, 45)))
            # start_point, end_point = st.slider('썸네일 탐색 구간', time(0,0,0), time(1,23,34),  value=(time(0, 2, 0), time(0, 4, 0)))
            st.write("start_point & end_point:", start_point, end_point)
        
        
        setup = {'genre': video_genre, 'start_point': start_point, 'end_point': end_point}
        gen_b = st.button('Generate')
    
    # 섬넬 추출 시작
    if gen_b:
        st.balloons()
        print(setup)
        requests.post(REST_API_URL+'/ai-thumbnail/setting', data=setup)
        
        selected_videos_index = np.array(file_index_list)[np.array(check_boxes)]
        selected_video_name = np.array(file_name_list)[np.array(check_boxes)]
        
        for i, video_inx in enumerate(selected_videos_index):
            data = {'index': video_inx}
            requests.post(REST_API_URL+'/ai-thumbnail/select-video', data=data)
            requests.post(REST_API_URL+'/ai-thumbnail/predict')
            
            video_inx = int(video_inx)
            st.write(selected_video_name[i])
            globals()['bar_{0}'.format(i)] = st.progress(0)
        
        run_number = len(selected_video_name)
        while(True):
            time.sleep(1)
            sum_percentage = 0
            for i in range(len(selected_video_name)):
                data = {'video_name': selected_video_name[i]}
                progress = requests.get(REST_API_URL+'/ai-thumbnail/progress', data=data)
                progress = progress.json()
                progress_percentage = progress['percentage']
                globals()['bar_{0}'.format(i)].progress(progress_percentage)
                sum_percentage += progress_percentage
            if sum_percentage == 100*run_number:
                break
        
        st.write('+++ All Completed +++')
        
        # output result images
        for i in range(len(selected_video_name)):
            data = {'video_name': selected_video_name[i]}
            comp_info = requests.get(REST_API_URL+'/ai-thumbnail/get-result', data=data)
            comp_info = comp_info.json()
            print(comp_info)
            
            st.subheader(f'Results of {selected_video_name[i]}')
            if comp_info['state'] == 'RUN_COMP':
                result_images = requests.get(REST_API_URL+'/ai-thumbnail/get-download-result', data=data)
                result_images = result_images.json()
                images = list(result_images.values())
                captions = list(result_images.keys())
                bytes_list = list(map(lambda x: base64.b64decode(x), images))
                image_list = list(map(lambda x: Image.open(io.BytesIO(x)), bytes_list))
                st.image(image_list, width=320, caption=captions)
                
                for num, image in enumerate(images):
                    filename = f'{selected_video_name[i][:-4]}_thumbnail.jpg'
                    href = f'<a href="data:file/jpg;base64,{image}" download="{filename}">Download {captions[num]}</a>'
                    st.markdown(href, unsafe_allow_html=True)
                
            elif comp_info['state'] == 'FAIL':
                st.info(comp_info['fail_reason'])


if __name__ == '__main__':
    ai_thumbnail_generation()
    
    