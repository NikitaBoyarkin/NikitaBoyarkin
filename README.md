<h3 align="center" > Hi Everyone!</h3>

- I am data analyst/ product analyst
  
- All my projects are available at [portfolio](https://nikitaboyarkin.github.io/Personal_Projects.github.io/)

- My [notes](https://nikitaboyarkin.github.io/digital_garden/) about **emotional** *intelligence* in IT


<h3 align="left">Languages and Tools:</h3>

<img src="assets/python-icon.svg" width="60" height="60">  <img src="assets/apache-airflow.svg" width="60" height="60">  <img src="assets/postgresql-icon.svg" width="60" height="60">  <img src="assets/clickhouse.svg" width="60" height="60">  <img src="assets/tableau-icon.svg" width="60" height="60">  <img src="assets/apache-superset-icon.svg" width="60" height="60"> <img src="assets/Docker Logo.svg" width="60" height="60"> <img src="assets/Obsidian Dark.svg" width="60" height="60">

<h3 align="left"> Connect with me </h3>
<div style="display: flex; justify-content: space-between; align-items: center;">
  <img src="assets/telegrem_qr_code.JPG" width="200" height="200" style="margin-right: 20px;">
  <img src="assets/сетка.JPG" width="200" height="200"tyle="margin-right: 20px;">
</div>

<style>
  /* Жирный текст */
strong, b {
    color: #ff6b6b; /* Красный оттенок */
}

/* Курсив */
em, i {
    color: #48dbfb; /* Голубой оттенок */
}

/* Зачеркнутый текст */
del, s {
    color: #1dd1a1; /* Зеленый оттенок */
}

/* Инлайн-код */
code {
    color: #f368e0; /* Фиолетовый оттенок */
    background-color: #f7f9fa;
    padding: 2px 4px;
    border-radius: 4px;
}

/* Подсветка при наведении */
strong:hover, b:hover,
em:hover, i:hover,
del:hover, s:hover,
code:hover {
    filter: brightness(85%);
}

</style>

<style>
  /* Базовая анимация появления */
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Анимация цветового градиента */
@keyframes gradientWave {
  0% {
    background-position: 0% 50%;
  }
  50% {
    background-position: 100% 50%;
  }
  100% {
    background-position: 0% 50%;
  }
}

/* Анимация подчеркивания */
@keyframes underline {
  from {
    width: 0;
  }
  to {
    width: 100%;
  }
}

/* Стили для заголовков */
h1, h2, h3, h4, h5, h6 {
  position: relative;
  animation: fadeIn 0.8s ease-out forwards;
  opacity: 0; /* Начальное состояние для анимации */
  
  /* Задержка анимации для разных уровней */
  &:nth-child(1) { animation-delay: 0.1s; }
  &:nth-child(2) { animation-delay: 0.2s; }
  &:nth-child(3) { animation-delay: 0.3s; }
}

/* Вариант 1: Анимированный градиентный текст */
.animated-gradient {
  background: linear-gradient(90deg, #ff6b6b, #48dbfb, #1dd1a1);
  background-size: 300% 300%;
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  animation: gradientWave 3s ease infinite;
}

/* Вариант 2: Анимированное подчеркивание */
.animated-underline {
  display: inline-block;
  padding-bottom: 5px;
  
  &::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    height: 3px;
    background: linear-gradient(90deg, #ff6b6b, #48dbfb);
    animation: underline 1.5s cubic-bezier(0.22, 0.61, 0.36, 1) forwards;
  }
}

/* Вариант 3: Трепещущий текст */
.animated-pulse {
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { transform: scale(1); }
  50% { transform: scale(1.05); }
  100% { transform: scale(1); }
}

/* Вариант 4: 3D-эффект */
.animated-3d {
  text-shadow: 
    0 1px 0 #ccc,
    0 2px 0 #bbb,
    0 3px 0 #aaa,
    0 4px 5px rgba(0,0,0,0.1);
  transform: translateY(-5px);
  transition: all 0.3s ease;
  
  &:hover {
    transform: translateY(0);
    text-shadow: 
      0 1px 0 #ccc,
      0 2px 0 #bbb,
      0 3px 5px rgba(0,0,0,0.1);
  }
}
</style>