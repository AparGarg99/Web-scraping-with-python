from fake_useragent import UserAgent
from selenium import webdriver
from selenium.webdriver import Chrome
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
import bs4
import pandas as pd
import time
import undetected_chromedriver as uc
import argparse
import random
import glob
import os
import urllib3
import warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore")

directory = './saved_checkpoints'
if not os.path.exists(directory):
    os.makedirs(directory)

def random_time_delay():
    time.sleep(random.uniform(40,80))


def open_driver(): 
    ua = UserAgent()
    chrome_options = uc.ChromeOptions()
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument('--disable-notifications')
    chrome_options.add_argument("--mute-audio")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument(f"user-agent={ua['google chrome']}")

    driver = uc.Chrome(executable_path=ChromeDriverManager().install(), options=chrome_options)
    
    return driver


def login(driver, username, password):
    # go to login page
    driver.get("https://www.instagram.com")
    random_time_delay()

    # Type username
    emailid = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.NAME, "username"))) 
    emailid.send_keys(username)
    random_time_delay()

    # Type password
    passwordid = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.NAME, "password")))
    passwordid.send_keys(password)
    random_time_delay()

    # Click on the signin button
    signinButton = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, '//*[@id="loginForm"]/div/div[3]/button/div')))
    ActionChains(driver).move_to_element(signinButton).click().perform()
    random_time_delay()
    
    return driver


def scroll(driver):
    # set load time
    scroll_pause_time = 5

    # Get screen height
    screen_height = driver.execute_script("return window.screen.height;")  
    i = 1

    while True:
        # scroll one screen height each time
        driver.execute_script(f"window.scrollTo(0, {screen_height}*{i});")
        i += 1

        # Wait to load page
        time.sleep(scroll_pause_time)

        # update scroll height each time after scrolled, as the scroll height can change after we scrolled the page
        scroll_height = driver.execute_script("return document.body.scrollHeight;")

        # Break the loop when the height we need to scroll is larger than the total scroll height
        if (screen_height) * i > scroll_height:
            break

    random_time_delay()
    
    return driver


def get_posts(driver):
    source = driver.page_source
    soup = bs4.BeautifulSoup(source, 'html.parser')
    posts = ['https://www.instagram.com'+div.find('a')['href'] for div in soup.find_all('div',{'class':'_aabd _aa8k _aanf'})]
    print('\tNo. of posts:',len(posts))
    return posts


def get_saved_users(posts):
    l = []
    
    for i,post in enumerate(posts):
        try:
            print('\tProcessing Posts:',i+1,'/',len(posts))
            
            driver.get(post)
            random_time_delay()

            source = driver.page_source
            soup = bs4.BeautifulSoup(source, 'html.parser')

            username = soup.find('span',{'class':'_aap6 _aap7 _aap8'}).text
            print(f'\t{username}')

            url = 'https://www.instagram.com/'+username

            l.append([post, url])

            # unsave post
            driver.find_element_by_css_selector('svg[aria-label="Remove"]').click()
            random_time_delay()

            print('\t'+'='*50)

        except Exception as e:
            print(e)
            pass
    return l


if __name__ ==  '__main__':
    
    ########################################## Get user input ##########################################
    parser = argparse.ArgumentParser("Scrape saved posts from an Instagram profile")
    parser.add_argument('-f', '--filepath', type=str, default='test_input_csv_files/saved_input.csv', help='Input file path containing channel login credentials to get users of saved posts (default = "test_input_csv_files/saved_input.csv")')
    parser.add_argument('-s', '--scroller', choices=['manual','auto'], default='auto', help='Scroll posts manually or automatically (default="auto")')
    args = parser.parse_args()

    credentials = pd.read_csv(args.filepath)
    print(credentials)

    ########################################## Scrape ##########################################
    df = []

    for j in range(len(credentials)):
        try:
            print('Processing Channel:', j+1, '/', len(credentials))
        
            # get instagram login credentials
            username = credentials.iloc[j,0]
            password = credentials.iloc[j,1]

            # open browser
            driver = open_driver()

            # login
            driver = login(driver, username, password)

            saved_posts_flag = True

            while(saved_posts_flag==True):
                # open saved posts page
                driver.get(f'https://www.instagram.com/{username}/saved/all-posts/')
                random_time_delay()

                # Infinite scrolling
                if(args.scroller=='auto'):
                    driver = scroll(driver)
                elif(args.scroller=='manual'):
                    print('Manually Scroll...')
                    time.sleep(5*60)

                # Get post links
                posts = get_posts(driver)
                if(len(posts)==0):
                    saved_posts_flag = False
                    continue

                # Get username from post links
                posts_data = get_saved_users(posts)
                
                # Add row to dataframe
                df.append([f'https://www.instagram.com/{username}', posts_data])

                # save checkpoint
                pd.DataFrame(df, columns = ['Channel','Saved data']).to_csv(f'{directory}/{j+1}.csv',index=False)

                print('\t'+'*'*100)

            # close browser
            driver.delete_all_cookies()
            driver.quit()
            random_time_delay()

        except Exception as e:
            print(e)
            pass

        print('#'*150)

    csv_files = glob.glob(f'{directory}/*')
    df2 = [pd.read_csv(i) for i in csv_files]
    df2 = pd.concat(df2, ignore_index=True)
    
    df2.to_csv('test_output_csv_files/saved_output.csv',index=False)

    try:
        df2['Saved data'] = df2['Saved data'].apply(lambda x: eval(x))
        df2 = df2.explode('Saved data', ignore_index=True)
        df2['Post url'] = df2['Saved data'].apply(lambda x: x[0].strip())
        df2['Post user'] = df2['Saved data'].apply(lambda x: x[1].strip())
        df2 = df2.drop('Saved data', axis=1).drop_duplicates()
    except:
        pass

    df2.to_csv('test_output_csv_files/saved_output.csv',index=False)