from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

print("starting! 1")
driver = webdriver.Chrome()
print("starting! 2")
driver.get("http://127.0.0.1:5500/tests/website/home.html")
print("starting! 3")

def click_element(xpath):
    try:
        element = driver.find_element(By.XPATH, xpath)
        element.click()
        time.sleep(1)
    except Exception as e:
        print(f"Error clicking element {xpath}: {e}")

# Start automation
click_element("//button[text()='Login']")
click_element("//button[text()='Movies']")

movies = ["mei.png", "inter.png", "gravity.png", "bladerunner.png"]
cycles = 5

print("starting!")
for _ in range(cycles):
    click_element("//button[text()='🎥 Rent Movie']")  # Go to Rent Movies
    for movie in movies:
        movie_xpath = f"//img[contains(@src, '{movie}')]"
        click_element(movie_xpath)
        click_element("//button[@id='pay-rent']")
        time.sleep(2)
        click_element("//button[text()='Go to Home']")
        click_element("//button[text()='Movies']")  # Navigate back to movies

print("Automation Completed")
driver.quit()
