import os

import bs4
import pymysql
import requests
# HTTPS
from fake_useragent import UserAgent
from pydub import AudioSegment
from selenium import webdriver

SOURCE_URL = 'https://www.examenglish.com/TOEIC/TOEIC_listening_part1.htm'

LISTENING = 1
READING = 2

AudioSegment.converter = "D:\\ffmpeg-20190323-5252d59-win64-static\\bin\\ffmpeg.exe"
AudioSegment.ffmpeg = "D:\\ffmpeg-20190323-5252d59-win64-static\\bin\\ffmpeg.exe"
AudioSegment.ffprobe = "D:\\ffmpeg-20190323-5252d59-win64-static\\bin\\ffmpeg.exe"

count = 1


def conn():
    return pymysql.connect(host='localhost',
                           user='root',
                           db='toeic_test',
                           charset='utf8',
                           cursorclass=pymysql.cursors.DictCursor)


def main():
    driver = webdriver.Chrome('E:/chromedriver_win32/chromedriver.exe')
    driver.implicitly_wait(5)
    driver.get(SOURCE_URL)
    s = bs4.BeautifulSoup(driver.page_source, 'lxml')
    title = s.select_one('div.panel-heading > h3').text
    title = title.split(':')[1].strip()
    print(title)
    description = s.select_one("div.panel-body > p").text.strip()
    print("description " + description)
    description_1 = s.select_one("div.panel-body").select_one("#testheader").text.strip()
    print("description_1 " + description_1)
    topicId = LISTENING
    id = updateTopicType(title, description, description_1, topicId)
    getQuestion(driver, s, id, topicId)


def updateTopicType(title, description, description_1, topicId):
    connection = conn()
    cursor = connection.cursor()
    id = cursor.execute("SELECT  id FROM topictype WHERE title = '%s'" % title)
    if id == 0:
        sql = "INSERT INTO `topictype` (idTopic ,title, recommend, instruction) VALUES (%s,%s, %s, %s)"
        val = (topicId, title, description, description_1)
        cursor.execute(sql, val)
        connection.commit()
        return cursor.lastrowid
    else:
        return id


def getQuestion(driver, s, idTypeTopic, topicId):
    global count
    image = s.select_one('div.panel-body > #centreposition > #image > img').attrs['src']
    print(image)
    image = downloadFile('images', image, True)
    print(image)
    if image:
        idQuestion = insertQuestion(idTypeTopic, topicId, image)
        if idQuestion != -1:
            driver.find_element_by_xpath('//*[@id="jplayer_play"]').click()
            listAudio = []
            while (True):
                try:
                    s = bs4.BeautifulSoup(driver.page_source, 'lxml')
                    audio = s.select_one('div.panel-body > #jquery_jplayer > #jqjp_audio_0').attrs['src']
                    if not listAudio.__contains__(audio):
                        listAudio.append(audio)
                except Exception as e:
                    print(e)
                    if listAudio:
                        break
                    else:
                        driver.implicitly_wait(0.5)
            print(listAudio)
            combined_sounds = AudioSegment.empty()
            answerA = {}
            answerB = {}
            answerC = {}
            answerD = {}
            if listAudio:
                del listAudio[0]
                audio = downloadFile('audio', listAudio[0], False)
                print(audio)
                if audio:
                    combined_sounds = AudioSegment.from_mp3(audio)
                for index, item in enumerate(listAudio, start=1):
                    audio = downloadFile('audio', item, False)
                    print(audio)
                    if audio:
                        if index == 2:
                            answerA['audio'] = audio.split('audio/')[1]
                        if index == 4:
                            answerB['audio'] = audio.split('audio/')[1]
                        if index == 6:
                            answerC['audio'] = audio.split('audio/')[1]
                        if index == 8:
                            answerD['audio'] = audio.split('audio/')[1]
                        combined_sounds += AudioSegment.from_mp3(audio)
            dirAudio = 'audio_question'
            if not os.path.isdir('audio_question'):
                os.mkdir('audio_question')

            audioQuestion = 'audio_question_type' + str(idTypeTopic) + '_id_' + str(idQuestion) + '.mp3'
            combined_sounds.export(dirAudio + '/' + audioQuestion, format="mp3")
            updateQuestion(idQuestion, audioQuestion)

            driver.find_element_by_xpath('//*[@id="scriptbutton"]').click()
            s = bs4.BeautifulSoup(driver.page_source, 'lxml')
            scrip = s.select_one('div.panel-body > #centreposition > #script3').contents
            answerContentA = str(scrip[1]).split('.')[1].strip()
            answerContentB = str(scrip[3]).split('.')[1].strip()
            answerContentC = str(scrip[5]).split('.')[1].strip()
            answerContentD = str(scrip[7]).split('.')[1].strip()
            answerA['content'] = answerContentA
            answerB['content'] = answerContentB
            answerC['content'] = answerContentC
            answerD['content'] = answerContentD
            print(answerA)
            print(answerB)
            print(answerC)
            print(answerD)

            updateAnswer(idQuestion, answerA['content'], answerA['audio'])
            updateAnswer(idQuestion, answerB['content'], answerB['audio'])
            updateAnswer(idQuestion, answerC['content'], answerC['audio'])
            updateAnswer(idQuestion, answerD['content'], answerD['audio'])

            answer_type = checkAnswer(driver)
            if answer_type == 1:
                updateAnswerQuestion(idQuestion, answerA['content'])
            elif answer_type == 2:
                updateAnswerQuestion(idQuestion, answerB['content'])
            elif answer_type == 3:
                updateAnswerQuestion(idQuestion, answerC['content'])
            elif answer_type == 4:
                updateAnswerQuestion(idQuestion, answerD['content'])

    driver.find_element_by_xpath('//*[@id="choices"]/input[1]').click()
    s = bs4.BeautifulSoup(driver.page_source, 'lxml')
    next = s.select_one('div.panel-body > #testfooter > #nextbutton > input').attrs['value']
    if 'Next' in next:
        driver.find_element_by_xpath('//*[@id="nextbutton"]').click()
        driver.implicitly_wait(5)
        s = bs4.BeautifulSoup(driver.page_source, 'lxml')
        getQuestion(driver, s, idTypeTopic, topicId)
    else:
        if count < 10:
            count += 1
            driver.refresh()
            driver.implicitly_wait(5)
            s = bs4.BeautifulSoup(driver.page_source, 'lxml')
            getQuestion(driver, s, idTypeTopic, topicId)


def downloadFile(dir, path, isImage):
    # tạo thư mục
    global url, file_name
    if not os.path.isdir(dir):
        os.mkdir(dir)

    if isImage:
        file_name = path.split('images/')[1]
    else:
        file_name = path.split('audio/')[1]

    if os.path.exists(dir + "/" + file_name):
        if isImage:
            return None
        else:
            return dir + '/' + file_name

    url = "https://www.examenglish.com/TOEIC/" + path
    print(url)

    ua_str = UserAgent().chrome
    response = requests.get(url, stream=True, headers={"User-Agent": ua_str})
    if response.status_code == 404:
        print('Error Not Found')
        print(url)
        return None
    with open(dir + '/' + file_name, 'wb') as out_file:
        out_file.write(response.content)

    print(response.status_code)
    print(response.headers['content-type'])

    if isImage:
        return file_name
    else:
        return dir + '/' + file_name


def insertQuestion(idTypeTopic, topicId, image):
    connection = conn()
    cursor = connection.cursor()
    if image:
        id = cursor.execute("SELECT  id FROM question WHERE image = '%s'" % image)
        if id == 0:
            sql = "INSERT INTO `question` (topicId ,topicTypeId, image, audio, content) VALUES (%s,%s, %s, %s,%s)"
            val = (topicId, idTypeTopic, image, None, None)
            cursor.execute(sql, val)
            connection.commit()
            return cursor.lastrowid
    return -1


def updateQuestion(idQuestion, audio):
    connection = conn()
    cursor = connection.cursor()
    cursor.execute("UPDATE question SET audio = '%s' WHERE id = %s" % (audio, idQuestion))
    connection.commit()


def updateAnswer(idQuestion, content, audio):
    connection = conn()
    cursor = connection.cursor()
    sql = "INSERT INTO `answer` (questionId ,questionChildId, content, audio) VALUES (%s,%s, %s, %s)"
    val = (idQuestion, None, content, audio)
    cursor.execute(sql, val)
    connection.commit()


def checkAnswer(driver):
    driver.find_element_by_xpath('//*[@id="choices"]/input[1]').click()
    s = bs4.BeautifulSoup(driver.page_source, 'lxml')
    answerQuestion = s.select_one('div.panel-body > #centreposition > #col1 > #form1').text
    if 'Correct' in answerQuestion:
        return 1
    driver.find_element_by_xpath('//*[@id="choices"]/input[2]').click()
    s = bs4.BeautifulSoup(driver.page_source, 'lxml')
    answerQuestion = s.select_one('div.panel-body > #centreposition > #col1 > #form1').text
    if 'Correct' in answerQuestion:
        return 2
    driver.find_element_by_xpath('//*[@id="choices"]/input[3]').click()
    s = bs4.BeautifulSoup(driver.page_source, 'lxml')
    answerQuestion = s.select_one('div.panel-body > #centreposition > #col1 > #form1').text
    if 'Correct' in answerQuestion:
        return 3
    driver.find_element_by_xpath('//*[@id="choices"]/input[4]').click()
    s = bs4.BeautifulSoup(driver.page_source, 'lxml')
    answerQuestion = s.select_one('div.panel-body > #centreposition > #col1 > #form1').text
    if 'Correct' in answerQuestion:
        return 4
    return -1


def updateAnswerQuestion(idQuestion, content):
    connection = conn()
    cursor = connection.cursor()
    sql = "INSERT INTO `answerquestion` (questionId ,questionChildId, content) VALUES (%s,%s, %s)"
    val = (idQuestion, None, content)
    cursor.execute(sql, val)
    connection.commit()


if __name__ == '__main__':
    main()
