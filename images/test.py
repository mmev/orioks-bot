from imager import Imager


img = Imager().get_image_marks(
    current_grade=15,
    max_grade=20,
    title_text='А/П.1 по «Метрология, стандартизация и сертификация в инфокоммуникациях: Методы и средства измерения в телекоммуникационных системах»',
    mark_change_text='0 —> 15 (из 20) (+ 15)',
    side_text='Изменён балл за контрольное мероприятие'
)


# img = Imager().get_image_news(
#     title_text='Выбор элективных и факультативных дисциплин на 1 семестр 2022-2023 уч.г.',
#     #title_text='Перевод в дистанционный режим обучения РТ-21, РТ-13, ЭН-22, ЭН-32, ПМ-21, П-21, Л-13, УТС-11М, ПИН -31, УТС-31, КТ-22, ЭН-34 в связи с возникшими случаями заболевания новой коронавирусной инфекцией (Covid-19)',
#     side_text='Опубликована новость',
#     url='https://orioks.miet.ru/main/view-news?id=474'
# )

