def get_content():
    blocks = []
    blocks.append({"type": "h1", "text": "СПИСОК ИСПОЛЬЗУЕМЫХ ИСТОЧНИКОВ И ЛИТЕРАТУРЫ"})
    
    references = [
        "1. Баранов А. Н. Введение в прикладную лингвистику. – М.: Эдиториал УРСС, 2021. – 360 с.",
        "2. Большакова Е. И., Воронцов К. В., Ефремова Н. Э., Клышинский Э. С., Лукашевич Н. В., Сафонов А. С. Автоматическая обработка текстов на естественном языке и анализ данных. – М.: Изд-во НИУ ВШЭ, 2017. – 269 с.",
        "3. Браславский П. И., Соколов Е. А. Информационный поиск и анализ текстов. – М.: Физматлит, 2020. – 220 с.",
        "4. Коршунов Антон, Гомзин Андрей. Тематическое моделирование текстов на естественном языке // Труды Института системного программирования РАН. – 2022. – Т. 23. – С. 215-244.",
        "5. Леонтьева Н. Н. Автоматическое понимание текстов: системы, модели, ресурсы. – М.: Издательский центр «Академия», 2018. – 304 с.",
        "6. Лукашевич Н. В. Тезаурусы в задачах информационного поиска. – М.: Изд-во МГУ, 2019. – 512 с.",
        "7. Маннинг К. Д., Рагхаван П., Шютце Х. Введение в информационный поиск. – М.: Вильямс, 2021. – 528 с.",
        "8. Рубцова Ю. В. Построение корпуса текстов для настройки тонового классификатора // Программные продукты и системы. – 2015. – №1 (109). – С. 72-78.",
        "9. Чуйкова Н. А., Юдина Л. С. Сравнительный анализ алгоритмов извлечения ключевых слов из русскоязычных текстов // Вестник МГТУ им. Н.Э. Баумана. – 2022. – № 2. – С. 14-25.",
        "10. Berry, M. W., Kogan, J. Text Mining: Applications and Theory. – Wiley, 2010. – 230 p.",
        "11. Blei, D. M., Ng, A. Y., Jordan, M. I. Latent Dirichlet Allocation // Journal of Machine Learning Research. – 2003. – Vol. 3. – P. 993-1022.",
        "12. Campos, R., Mangaravite, V., Pasquali, A., Jorge, A., Nunes, C., Jatowt, A. YAKE! Keyword extraction from single documents using multiple local features // Information Sciences. – 2020. – Vol. 509. – P. 257-289.",
        "13. Carbonell, J., Goldstein, J. The Use of MMR, Diversity-Based Reranking for Reordering Documents and Producing Summaries // Proceedings of the 21st Annual International ACM SIGIR Conference. – 1998. – P. 335-336.",
        "14. Devlin, J., Chang, M.-W., Lee, K., Toutanova, K. BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding // Proceedings of NAACL-HLT. – 2019. – P. 4171-4186.",
        "15. Grootendorst, M. KeyBERT: Minimal keyword extraction with BERT // GitHub Repository. – 2020. – URL: https://github.com/MaartenGr/KeyBERT (дата обращения: 10.05.2026).",
        "16. Hasan, K. S., Ng, V. Automatic Keyphrase Extraction: A Survey of the State of the Art // Proceedings of the 52nd Annual Meeting of the Association for Computational Linguistics. – 2014. – P. 1262-1273.",
        "17. Jones, K. S. A statistical interpretation of term specificity and its application in retrieval // Journal of Documentation. – 1972. – Vol. 28. – P. 11-21.",
        "18. Lin, C.-Y. ROUGE: A Package for Automatic Evaluation of Summaries // Text Summarization Branches Out. – 2004. – P. 74-81.",
        "19. Manning, C. D., Surdeanu, M., Bauer, J., Finkel, J., Bethard, S., McClosky, D. The Stanford CoreNLP Natural Language Processing Toolkit // Proceedings of the 52nd Annual Meeting of the Association for Computational Linguistics: System Demonstrations. – 2014. – P. 55-60.",
        "20. Mihalcea, R., Tarau, P. TextRank: Bringing Order into Texts // Proceedings of EMNLP. – 2004. – P. 404-411.",
        "21. Mikolov, T., Sutskever, I., Chen, K., Corrado, G. S., Dean, J. Distributed Representations of Words and Phrases and their Compositionality // Advances in Neural Information Processing Systems. – 2013. – P. 3111-3119.",
        "22. Neo4j Graph Database. Official Documentation [Электронный ресурс]. – URL: https://neo4j.com/docs/ (дата обращения: 12.05.2026).",
        "23. Page, L., Brin, S., Motwani, R., Winograd, T. The PageRank Citation Ranking: Bringing Order to the Web. – Stanford InfoLab, 1999. – 17 p.",
        "24. Pennington, J., Socher, R., Manning, C. D. GloVe: Global Vectors for Word Representation // Proceedings of the 2014 Conference on Empirical Methods in Natural Language Processing (EMNLP). – 2014. – P. 1532-1543.",
        "25. Reimers, N., Gurevych, I. Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks // Proceedings of the 2019 Conference on Empirical Methods in Natural Language Processing. – 2019. – P. 3982-3992.",
        "26. Robertson, S. E. Understanding Inverse Document Frequency: On theoretical arguments for IDF // Journal of Documentation. – 2004. – Vol. 60. – P. 503-520.",
        "27. Rose, S., Engel, D., Cramer, N., Cowley, W. Automatic Keyword Extraction from Individual Documents // Text Mining: Applications and Theory. – 2010. – P. 1-20.",
        "28. Salton, G., Buckley, C. Term-weighting approaches in automatic text retrieval // Information Processing & Management. – 1988. – Vol. 24. – P. 513-523.",
        "29. Scikit-learn: Machine Learning in Python [Электронный ресурс]. – URL: https://scikit-learn.org/ (дата обращения: 11.05.2026).",
        "30. Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A. N., Kaiser, L., Polosukhin, I. Attention Is All You Need // Advances in Neural Information Processing Systems. – 2017. – P. 5998-6008."
    ]
    
    for ref in references:
        blocks.append({"type": "p", "text": ref, "indent": None})

    return blocks
