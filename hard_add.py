from selenium import webdriver
from selenium.webdriver.chrome.options import Options


def cookie_add(cookie_list: list, name: str, value: str, domain: str = 'csgostats.gg', path: str = '/'):
    cookie_list.append({
        'name': name,
        'value': value,
        'domain': domain,
        'path': path
    })


def add_match(sharecode: str):

    chrome_options = Options()
    chrome_options.add_argument("user-agent=suppes match adder")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    cookies = []
    cookie_add(cookies, '__cf_bm', '63d33b62027ee4d0a5f690eabd378578e299fa3e-1595250139-1800-Aa5GbuMHOaiE8nX3RE3DwxqQZls9X5GkRZ46Fw7+oTdkgEIHwV1xHiSFFNBbxgAcdhBckg3kUMSWRQOCMb/kaz4B7sqUKLJv42cU0KQ4I0ilfqMwrfNfgPWzSVGXXQtEtQ==')

    with webdriver.Chrome(options=chrome_options) as driver:
        # print('Loading Site')
        driver.get('https://csgostats.gg/')
        [driver.add_cookie(i) for i in cookies]
        # print('Loaded Site')
        driver.find_element_by_xpath('/html/body/div[3]/div/form/button').click()
        # print('Clicking: "Accept cookies"')
        driver.find_element_by_xpath('/html/body/div[2]/div[1]').click()
        # print('Clicking: "Add Match"')
        code = driver.find_element_by_xpath('/html/body/div[2]/div[2]/div[2]/div[2]/form/input')
        code.send_keys(sharecode)
        # print('Sending Sharecode')
        driver.find_element_by_xpath('/html/body/div[2]/div[2]/div[2]/div[2]/form/button').click()
        # print('Clicking: "Submit"')
        driver.save_screenshot('test.png')
    return 'Added {} to csgostats.gg'.format(sharecode)


