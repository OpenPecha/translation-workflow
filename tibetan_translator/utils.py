import json
import logging
from tibetan_translator.models import State
from langchain_anthropic import ChatAnthropic
import os
from langchain_core.messages import HumanMessage, SystemMessage

# Import configuration - this will load environment variables from .env
from tibetan_translator.config import LLM_MODEL_NAME, MAX_TOKENS

# Setup logging - file only to avoid interfering with tqdm progress bars
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("translation_debug.log")
        # StreamHandler removed to prevent console output that breaks tqdm
    ]
)
logger = logging.getLogger("tibetan_translator")

# Define few-shot examples for translation extraction in different languages
translation_extraction_examples = [
    # English example
    {"source": "བཅོམ་ལྡན་འདས་རྒྱལ་པོའི་ཁབ་བྱ་རྒོད་ཕུང་པོའི་རི་ལ་དགེ་སློང་གི་དགེ་འདུན་ཆེན་པོ་དང་།",
     "translation": "The Blessed One was residing on Vulture Peak Mountain in Rajagriha with a great assembly of monks.",
     "language": "English",
     "llm_response": "I've analyzed the Tibetan text and here's my translation:\n\nThe Blessed One was residing on Vulture Peak Mountain in Rajagriha with a great assembly of monks.\n\nThis is a common opening formula in many Buddhist sutras, indicating where the Buddha was teaching."},
    
    # Chinese example
    {"source": "འདི་སྐད་བདག་གིས་ཐོས་པ་དུས་གཅིག་ན།",
     "translation": "如是我聞，一時，",
     "language": "Chinese", 
     "llm_response": "翻译：\n如是我聞，一時，\n\n解释：这是佛经的标准开头，表示'这是我听到的'，由阿难在佛陀涅槃后结集经典时所加。"},
     
    # Italian example
    {"source": "བཅོམ་ལྡན་འདས་མཉན་ཡོད་ན་རྒྱལ་བུ་རྒྱལ་བྱེད་ཀྱི་ཚལ་མགོན་མེད་ཟས་སྦྱིན་གྱི་ཀུན་དགའ་ར་བ་ན།",
     "translation": "Il Beato soggiornava a Śrāvastī, nel boschetto di Jeta, nel giardino di Anāthapiṇḍika.",
     "language": "Italian",
     "llm_response": "Ecco la traduzione del testo tibetano:\n\nIl Beato soggiornava a Śrāvastī, nel boschetto di Jeta, nel giardino di Anāthapiṇḍika.\n\nNote: Questo è un tipico inizio di un sutra buddhista che indica dove il Buddha stava insegnando. Śrāvastī era una città importante nell'India antica."},
     
    # Russian example
    {"source": "དགེ་སློང་དག་ངས་མྱ་ངན་ལས་འདས་པའི་བར་དུ་སྡུག་བསྔལ་རྒྱུ་མཚན་འགོག་པའི་ལམ་བསྟན་ཏོ།",
     "translation": "Монахи, вплоть до моей нирваны я учил о страдании, его причине, прекращении и пути.",
     "language": "Russian",
     "llm_response": "Я перевел текст на русский язык:\n\nМонахи, вплоть до моей нирваны я учил о страдании, его причине, прекращении и пути.\n\nЭто относится к Четырем Благородным Истинам, которые являются фундаментальным учением Будды."}
]


# Define few-shot examples for plain translation
plain_translation_examples = [
    {
        "source":"དགེ་བ་གཞན་ཀུན་ཆུ་ཤིང་བཞིན་དུ་ནི། །\nའབྲས་བུ་བསྐྱེད་ནས་ཟད་པར་འགྱུར་བ་ཉིད། །\nབྱང་ཆུབ་སེམས་ཀྱི་ལྗོན་ཤིང་རྟག་པར་ཡང་། །\nའབྲས་བུ་འབྱིན་པས་མི་ཟད་འཕེལ་བར་འགྱུར། །\n",
        "plaintext_translation":"All other virtuous deeds are like plantain trees—they bear fruit once and then are exhausted. But the tree of the awakening mind is different: it continually produces fruit without ever becoming depleted, and instead grows ever more abundant.\n\nJust as plantain trees wither away after bearing their single harvest, likewise all virtuous actions not embraced by the awakening mind will eventually be consumed after yielding their results. In contrast, the tree of bodhicitta—the mind aspiring to enlightenment for the benefit of all beings—constantly bears fruit that never diminishes. Rather than becoming exhausted, its beneficial results perpetually increase and multiply."
    },
    {
        "source":"སྡིག་པ་ཤིན་ཏུ་མི་བཟད་བྱས་ན་ཡང་། །\nདཔའ་ལ་བརྟེན་ནས་འཇིགས་པ་ཆེན་པོ་ལྟར། །\nགང་ལ་བརྟེན་ནས་ཡུད་ཀྱིས་སྒྲོལ་འགྱུར་བ། །\nདེ་ལ་བག་ཅན་རྣམས་ཀྱིས་ཅིས་མི་བརྟེན། །\n",
        "plaintext_translation":"Even if one has committed the most terrible negative actions,Like a person who gains protection from great dangers by relying on a brave protector,By relying on bodhicitta, one can be swiftly liberated in an instant.So why would conscientious people not rely on this?"
    }
]

# Define few-shot examples for combined commentary in multiple languages
combined_commentary_examples = [
    # English examples
    {
        "source": "དགེ་བ་གཞན་ཀུན་ཆུ་ཤིང་བཞིན་དུ་ནི། །\nའབྲས་བུ་བསྐྱེད་ནས་ཟད་པར་འགྱུར་བ་ཉིད། །\nབྱང་ཆུབ་སེམས་ཀྱི་ལྗོན་ཤིང་རྟག་པར་ཡང་། །\nའབྲས་བུ་འབྱིན་པས་མི་ཟད་འཕེལ་བར་འགྱུར། །\n",
        "commentaries": "Commentary 1: This verse compares the merit of ordinary virtuous actions to the merit of actions motivated by bodhicitta, the mind of enlightenment. Ordinary virtues, like plantain trees, produce fruit once and then are depleted, while virtues motivated by bodhicitta are inexhaustible and continue to increase.\n\nCommentary 2: In this verse, all virtuous actions that are not embraced by bodhicitta are compared to plantain trees, which bear fruit once and die. By contrast, the tree of bodhicitta constantly produces fruit without becoming exhausted, and instead continues to grow. This is because ordinary virtue, once it has ripened into a fortunate rebirth, is depleted, while virtue dedicated to enlightenment for the benefit of all beings continues to bear fruit until enlightenment.\n\nCommentary 3: The first line refers to ordinary virtuous deeds that are not embraced by bodhicitta. These are compared to plantain trees, which after bearing fruit once, become exhausted. The Sutralamkara states: \"Just as a plantain tree dies after bearing fruit, and a stone that is thrown into the sky falls back to earth when its momentum is exhausted, likewise ordinary virtues are depleted after producing their results.\" In contrast, virtuous deeds embraced by bodhicitta are like wish-fulfilling trees that continually bear fruit without being exhausted and increase more and more.",
        "combined_commentary": "དགེ་བ་གཞན་ཀུན་ཆུ་ཤིང་བཞིན་དུ་ནི། །\n(All other virtuous actions are like plantain trees)\n\nThis verse compares all virtuous actions not embraced by bodhicitta to plantain (or banana) trees. Just as the trunk of a plantain tree bears fruit only once and then becomes exhausted, similarly all other kinds of merit not embraced by bodhicitta will eventually be depleted after ripening. These virtuous actions that accord with ordinary merit will produce temporary fruits such as higher rebirth but then become exhausted.\n\nའབྲས་བུ་བསྐྱེད་ནས་ཟད་པར་འགྱུར་བ་ཉིད། །\n(After bearing fruit, they become exhausted)\n\nAfter producing their results, these ordinary virtuous actions are depleted, just as the plantain tree dies after bearing fruit. Even the spiritual accomplishments of Śrāvakas and Pratyekabuddhas ultimately reach a state where their aggregates become extinguished without remainder, as they lack the inexhaustible quality that bodhicitta provides.\n\nབྱང་ཆུབ་སེམས་ཀྱི་ལྗོན་ཤིང་རྟག་པར་ཡང་། །\n(But the tree of bodhicitta constantly)\n\nIn contrast, virtuous actions embraced by bodhicitta are compared to excellent wish-fulfilling trees. The Precious Casket Sūtra explains: \"Mañjuśrī, it is like this: various trees grow and flourish when sustained by the four elements. Likewise, when the roots of virtue are embraced by the mind of enlightenment and dedicated to omniscience, they flourish and increase.\"\n\nའབྲས་བུ་འབྱིན་པས་མི་ཟད་འཕེལ་བར་འགྱུར། །\n(Produces fruit without exhaustion and continues to increase)\n\nThe tree of bodhicitta constantly and continuously yields the ripened fruit of temporary excellent happiness for gods and humans, which is never exhausted. The fruit increases progressively and ultimately produces the vast results counted among the merit accumulations of the Buddha's form body. As stated in the Akṣayamati-nirdeśa Sūtra: \"Just as water droplets that fall into the great ocean are not exhausted until the end of the kalpa, likewise virtuous deeds dedicated to enlightenment are not exhausted until the attainment of the essence of enlightenment.\" This is the fourth point illustrating the benefits of bodhicitta.",
        "language": "English"
    },
    {
        "source": "སྡིག་པ་ཤིན་ཏུ་མི་བཟད་བྱས་ན་ཡང་། །\nདཔའ་ལ་བརྟེན་ནས་འཇིགས་པ་ཆེན་པོ་ལྟར། །\nགང་ལ་བརྟེན་ནས་ཡུད་ཀྱིས་སྒྲོལ་འགྱུར་བ། །\nདེ་ལ་བག་ཅན་རྣམས་ཀྱིས་ཅིས་མི་བརྟེན། །\n",
        "commentaries": "Commentary 1: This verse illustrates how bodhicitta can purify even the most severe negative actions. Just as a criminal might seek protection from a powerful person, someone who has committed serious misdeeds can be protected from their karmic results by relying on bodhicitta.\n\nCommentary 2: Even if one has committed the most unbearable negative actions, such as the five actions with immediate retribution, they can be swiftly liberated by relying on bodhicitta, just as someone in great danger can find protection by relying on a powerful hero. Therefore, those who are conscientious should definitely rely on bodhicitta.\n\nCommentary 3: This verse shows how powerful bodhicitta is in purifying negative karma. The Teaching of Inexhaustible Intelligence states: \"Just as a person can avoid all enemies by relying on a brave hero, similarly a bodhisattva who properly relies on the brave mind of bodhicitta is not afraid of any negative actions.\" This is the fifth benefit of bodhicitta—its ability to destroy negative karma from its root.",
        "combined_commentary": "སྡིག་པ་ཤིན་ཏུ་མི་བཟད་བྱས་ན་ཡང་། །\nEven if one has committed extremely unbearable negative actions such as abandoning the Dharma, harming the Three Jewels, or committing the five heinous acts that would certainly lead to experiencing the sufferings of the Avīci hell,\n\nདཔའ་ལ་བརྟེན་ནས་འཇིགས་པ་ཆེན་པོ་ལྟར། །\njust as a criminal who has committed terrible deeds might be protected from great dangers by relying on a brave escort or hero (like a person who has killed someone's father seeking protection from a powerful person against the vengeful son),\n\nགང་ལ་བརྟེན་ནས་ཡུད་ཀྱིས་སྒྲོལ་འགྱུར་བ། །\nsimilarly, by relying on the precious bodhicitta, one will be swiftly liberated in an instant from the ripening effects of those great negative actions—the sufferings of lower rebirths and hell realms,\n\nདེ་ལ་བག་ཅན་རྣམས་ཀྱིས་ཅིས་མི་བརྟེན། །\nso why would those who are conscientious about observing what should be adopted and rejected, and who fear negative actions, not rely on this bodhicitta? As stated in the Teaching of Inexhaustible Intelligence (Akṣayamatinirdeśa): \"Son of noble family, it is like this: One who relies on a brave person is not afraid of any enemies. Similarly, a bodhisattva who properly relies on the brave person who has generated bodhicitta is not afraid of any enemies of wrongdoing.\" This is the fifth point, illustrating how bodhicitta, like fire, destroys sin from its root.",
        "language": "English"
    },
    
    # Chinese examples
    {
        "source": "བདེ་གཤེགས་ཆོས་ཀྱི་སྐུ་མངའ་སྲས་བཅས་དང་། །ཕྱག་འོས་ཀུན་ལའང་གུས་པར་ཕྱག་འཚལ་ཏེ། །བདེ་གཤེགས་སྲས་ཀྱི་སྡོམ་ལ་འཇུག་པ་ནི། །ལུང་བཞིན་མདོར་བསྡུས་ནས་ནི་བརྗོད་པར་བྱ། །\n",
        "commentaries": """评论1: 所谓"顶礼"，向谁顶礼呢？通过菩萨乘这一安乐之道而到达圆满佛果安乐之处，故称"善逝"，这表示佛宝。若从梵文"苏嘎达"来解释，"苏"是善好、庄严、安乐之义，"嘎达"是"去"之义，因此有三种含义：善妙庄严而去、永不退转而去、圆满无余而去。佛陀世尊具有证悟或教法法身之自在，故说"具法身"表示法宝。"及佛子"等表示僧宝。一般而言，身子舍利弗，语子声闻缘觉，意子菩萨。及具此三宝，不仅如此，还包括声闻、缘觉以及戒腊高于自己者，乃至于任何以一德超胜及饶益等一切应礼敬者。为何目的？为使造论无碍圆满，也为使后学对论典生起正信而欲求，讲闻无碍圆满。

评论2: "善逝"(sugata)一词可从断除和证悟两个方面来解释。关于圆满断除的功德：如同相貌端正之人，他已完全断除烦恼障而优美庄严地前行；如同病痊愈之人，他不会因烦恼而重返轮回；如同盛满之瓶，他已断尽非烦恼性的无明而无余地前行，故称善逝。法身是本性清净的法界远离一切垢染，即是法宝，具足此法身者即是善逝。"佛子"指圣位菩萨，与之相应即是三宝。对这些以及其他一切应受礼敬者，如亲教师、轨范师等，都以三门恭敬顶礼。

评论3: 关于"善逝"，因为善妙而去，故称善逝。就如说"美好的形象"、"病已痊愈"、"瓶子盛满"一样，是指断除烦恼等障碍后庄严地前行，以及清除遮蔽真如的无明等后永不退转地前行，并且清除一切习气后圆满地前行。法身，如《宝性论》中说："法身当知有二种，极清净法界，及其随顺因，深奥与广大，诸法皆显示。"佛子，如《宝性论》中说："于胜乘起信为种子，智慧为生佛法之母，禅定安乐为胎藏，大悲为乳母，此即牟尼之佛子。"如此作礼敬的功德，如《赞佛功德经》中说："若人于善逝，作少分供养，历经人天乐，终证无死果。\"""",
        "combined_commentary": """# 顶礼与目的陈述

བདེ་གཤེགས་ཆོས་ཀྱི་སྐུ་མངའ་སྲས་བཅས་དང་། །
(向具有法身的善逝及其子众礼敬)

"善逝"(བདེ་གཤེགས་)一词可从佛陀断除障碍的三个角度来理解。首先，如同相貌端正之人，佛陀已完全断除情绪性烦恼(烦恼障)而庄严前行。其次，如同病已痊愈之人，佛陀因彻底根除自我执著的种子而永不再返轮回。第三，如同盛满之瓶，佛陀已完全无余地断除所知障。这三方面分别将佛陀与世间的出离者、预流果及声闻阿罗汉区分开来。

从圆满证悟的角度，"善逝"也表示已完全证悟二无我、证悟不退转、证悟无余者。如《菩萨地》所说："佛陀被称为'善逝'，因为他已到达最殊胜境界并且永不退转地前行。"

"具有法身"(ཆོས་ཀྱི་སྐུ་མངའ་)指佛陀对究竟法的体现。如《宝性论》所解释："法身应当了知为二种：极其清净的法界以及与之相应的因，包括显示一切方面的深广教法。"这既指证悟法身——与无漏智慧不可分离的完全清净法界，也指教法法身——基于二谛的深广教法。这表示法宝。

"及其子众"(སྲས་བཅས་)指圣位菩萨。如《宝性论》所述："于胜乘的信心为种子，智慧为生佛功德之母，禅定安乐为胎藏，大悲为乳母——这些是牟尼的子众。"这些菩萨生于佛陀家族并继承其传承，代表僧宝。

ཕྱག་འོས་ཀུན་ལའང་གུས་པར་ཕྱག་འཚལ་ཏེ། །
(及一切应礼敬者，我恭敬顶礼)

作者不仅向上述三宝致敬，还向声闻、缘觉、亲教师及所有因其殊胜功德而应受尊敬的人致敬。这一礼敬通过身、语、意三门恭敬进行。如龙树所说，此礼敬的目的是"确保著作的成功完成，并在未来学生中对导师和论著生起信心与兴趣。"《广大游戏经》确认："善业成熟为安乐，消除一切苦。具足福德者，成就一切愿。"

བདེ་གཤེགས་སྲས་ཀྱི་སྡོམ་ལ་འཇུག་པ་ནི། །
(入善逝子众之律仪)

这指菩萨律仪的全面修持，包括防恶行戒、摄善法戒以及饶益有情戒。这是从最初发菩提心，经由六波罗蜜多的修持，直至证得佛果的完整道路。将此仅解释为伦理学是过于狭隘的。

ལུང་བཞིན་མདོར་བསྡུས་ནས་ནི་བརྗོད་པར་བྱ། །
(我将依照经教，简要解说)

作者回应一个潜在的质疑："既然佛陀教法已经完好保存，撰写另一部论著岂非多余？"实际上，这项努力并无过失。佛陀教法浩瀚众多，在当今末法时期，众生寿命短暂，智慧与精进薄弱，无法理解或正确修持如此广大的教法。因此，出于对这些众生的大悲心，作者撰写此论，将分散的教法汇集为单一、易于理解的修行手册。

根据传统分类，论著有四种目的：整理混乱材料、阐明隐晦义理、汇集分散教法以及提供实修指导。此论主要实现后两种功能。通过声明"依照经教"撰写此论，作者向读者保证这不是个人创作，而是忠实呈现佛陀意趣，从而生起信心。如量论所述："经教为可信之语，因为无过者不会妄语。"

作者承诺撰写此论确保其完成，因为圣者从不放弃承诺。如《智慧树》所述："圣者不轻易承诺；一旦承担艰难任务，如同刻在石上的铭文——纵使死亡也不改变。\"""",
        "language": "Chinese"
    },
    {
        "source": "སྔོན་ཆད་མ་བྱུང་བ་ཡང་འདིར་བརྗོད་མེད། །སྡེབ་སྦྱོར་མཁས་པའང་བདག་ལ་ཡོད་མིན་ཏེ། །དེ་ཕྱིར་གཞན་དོན་བསམ་པ་བདག་ལ་མེད། །རང་གི་ཡིད་ལ་བསྒོམ་ཕྱིར་ངས་འདི་བརྩམས། །",
        "commentaries": """评论1: 在此经中没有阐述过去诸佛世尊和龙树等未曾宣说的其他深奥义理。虽然如毗布提月所说：虽然佛教中出现了许多伟大的人物，但找不到如寂天一般具有如此境界和意趣的人。这句话确实符合事实，但他仍然保持谦逊。虽然像《三十四本生传》和《善慧王本生传》等佛经中所说的佛陀本生故事，以诗歌格律和修辞而成为令智者欢喜的论著，但我寂天并不具备这样卓越的诗歌创作才能。因此，我写作此《入菩萨行论》时，并没有想着能够成就广大的利他事业，这是对文字和义理方面才智的慢心的断除。那么，写作此论有何必要呢？是为了在自己的心中修习菩提心和六波罗蜜多等菩萨行，因为在讲说、辩论、著作三者中，著作是修习和熟练的最佳方式，所以我写作了这部论著。如月称论师所说：因为智者的三种事业中，讲说和辩论二者不确定，所以著作是不会错误的。这样做的目的是为了避免过失，因为慢心的高地上无法积聚功德之水，如果内心充满我慢，不仅无法保持教证和证悟的殊胜功德，还会被魔所欺，所著论典也不会对他人有益。

评论2: 如果只是按照经典原样陈述，就应当依据经典来理解，那为什么还要撰写此论呢？为了帮助其他通过依靠经典而能轻易理解其义的人，我撰写了这部论著。在这部论著中，没有丝毫阐述在经典中前所未有的内容。虽然意义上没有差别，但在文字的轻重组合等诗律技巧方面，我也并不精通。这就是这两个原因。其二是：寂天撰写此论有其必要，因为是为了使已经了知的内容不退失并增长，以便于自心熟习。这里用此这个近指词，是指导师心中已完成的部分，或者表示这是正在撰写的，尚未完成之意。若有人问：如果是为自己而写，在未通达之时写论不合理，若已通达则应当修习即可，何必撰写论典？对此无过失，因为这是为了持续不断地修习广大善行，而且将其写成论典也能使心意逐渐增长。因此，我的信心、智慧、悲心等力量，通过写成论典，首先会在自己相续中增长，之后，与此论有缘的其他人也将通达。暂时和而这些词的力量，暗示了利益他人的意义。

评论3: 此处没有阐述任何经典等中前所未有的义理，我寂天也不具备前所未有的诗歌创作技巧。因这两个原因，我并非为利他而造此论。那么为何要造呢？我造此论是为了在自己心中修习菩提心。如此说来，自己了知就足够了，那么造论有何必要呢""",
        "combined_commentary": """# 谦虚与创作意图

སྔོན་ཆད་མ་བྱུང་བ་ཡང་འདིར་བརྗོད་མེད། ། (此中未说昔所无)
在此偈颂中，寂天菩萨展现了深切的谦逊，承认他并未提出任何过去诸佛及龙树等大成就者未曾教导过的新颖或前所未有的教义。尽管毗布提月 (Vibhutichandra) 曾赞叹道："佛教虽出现过许多伟大的人物，但找不到如寂天一般具有如此境界和意趣的人"，作者依然保持谦逊姿态。这种谦逊是为了避免骄慢之过，正如传统所教导的那样，（骄慢者）"无法在傲慢的高地上积聚功德之水"。

སྡེབ་སྦྱོར་མཁས་པའང་བདག་ལ་ཡོད་མིན་ཏེ། ། (亦不善于诗词论)
寂天继续其谦逊的表述，声称自己缺乏如《三十四本生传》(Thirty-four Jataka Stories) 和《善慧王本生传》(Jataka of King Suvarna) 等典籍中所展现的诗歌文采和文学技巧，这些典籍以其精妙的格律 (meter) 和修辞 (rhetoric) 令智者欢喜。虽然他所传达的意义与经藏无异，但他承认自己在文字的艺术编排、韵律 (rhythm) 和诗歌技巧方面有所欠缺。这旨在消除对文学成就的任何骄傲。

དེ་ཕྱིར་གཞན་དོན་བསམ་པ་བདག་ལ་མེད། ། (故吾不曾思利他)
基于这两个限制——即未提出新内容且缺乏诗才——寂天声称他撰写此文并非以利益他人为首要意图。这对于一位菩萨而言似乎自相矛盾，但正如月称论师 (Chandrakirti) 所指出："在讲说、辩论、著作三种智者事业中，讲说和辩论二者不确定，所以著作是（最）不会错误的。" 这种表面上否认利他意图的说法，实际上展现了寂天已远离骄慢，因为他认识到，带着过分自我重要感写成的论典很少能利益他人，甚至可能使作者易受魔扰。

རང་གི་ཡིད་ལ་བསྒོམ་ཕྱིར་ངས་འདི་བརྩམས། ། (为修自心撰此论)
此处寂天揭示了他真正的目的：为了在他自己的心续中修习菩提心和六度波罗蜜 (six perfections)。著述的过程有助于防止理解力的衰退，并支持对这些教义的持续熟悉。在讲说、辩论、著作这三种智者事业中，写作被认为最有利于深度融合教义。指示词"此"(འདི། - 'di) 要么指作者心中已完成的部分，要么表示在撰写此偈时此著作仍在进行中。
尽管寂天声称他是为自利而写作，但（上一句的）"因此"(དེ་ཕྱིར། - de phyir) 一词巧妙地暗示了他人也能获益。通过撰写此文，寂天自身的信心、智慧和悲心得以增长，随后，与此论有殊胜因缘者也将通达其义。因此，此论虽主要为自我修持而作，最终却服务于自他二利的双重目的。""",
        "language": "Chinese"
    }
]

def get_translation_extraction_prompt(source_text, llm_response, language="English"):
    """Generate a few-shot prompt for translation extraction with language-specific examples."""
    system_message = SystemMessage(content=f"""You are an expert assistant specializing in extracting translations in {language} from text. Your task is to:

1. Identify the actual translation portion of the text that is in {language}
2. Extract ONLY the {language} translation, not any translator's notes, explanations, or formatting instructions
3. Preserve the exact formatting of the translation including line breaks
4. Remove any metadata, headers, or annotations that are not part of the translation itself
5. VERIFY that the extracted text is actually in {language}

CRITICAL: If the text contains translation in a language other than {language}, do NOT extract it. Your extracted text MUST be entirely in {language}.

DO NOT include any explanatory text or commentary in your extraction. Return ONLY the translation text in {language}.""")
    
    # Create few-shot examples as a conversation
    messages = [system_message]
    
    # Filter examples to include one in the target language, and at least one in another language
    target_lang_examples = []
    other_lang_examples = []
    
    for example in translation_extraction_examples:
        if example['language'].lower() == language.lower():
            target_lang_examples.append(example)
        else:
            other_lang_examples.append(example)
    
    # Ensure we have at least one example in the target language
    examples_to_use = target_lang_examples[:1]  # Take one target language example
    
    # Add one non-target language example to show what NOT to extract
    if other_lang_examples:
        examples_to_use.append(other_lang_examples[0])
    
    # Add more target language examples if available
    if len(target_lang_examples) > 1:
        examples_to_use.extend(target_lang_examples[1:2])  # Add one more target language example if available
    
    # Add few-shot examples
    for example in examples_to_use:
        # Add user message with request - include actual LLM response patterns if available
        llm_resp = example.get('llm_response', f"Here's my translation of the Tibetan text:\n\n{example['translation']}\n\nNote: This is a translation of the original text.")
        
        # For non-target language examples, modify the instruction to show what NOT to extract
        if example['language'].lower() != language.lower():
            messages.append(HumanMessage(content=f"""Extract the {language} translation from the following text (if present):

SOURCE TEXT:
{example['source']}

LLM RESPONSE:
{llm_resp}
"""))
            # Empty response for non-target language (nothing to extract)
            messages.append({"type": "ai", "content": "The provided text does not contain a translation in " + language + "."})
        else:
            messages.append(HumanMessage(content=f"""Extract the {language} translation from the following text:

SOURCE TEXT:
{example['source']}

LLM RESPONSE:
{llm_resp}
"""))
            # Correct response for target language
            messages.append({"type": "ai", "content": example['translation']})
    
    # Add the actual request
    messages.append(HumanMessage(content=f"""Extract the {language} translation from the following text:

SOURCE TEXT:
{source_text}

LLM RESPONSE:
{llm_response}

Remember: Extract ONLY the {language} translation portion, no explanatory text or metadata. If the text does not contain a translation in {language}, state that no {language} translation is present."""))
    
    return messages

def get_plain_translation_prompt(source_text, language="English"):
    """Generate a few-shot prompt for plain language translation using a multi-turn conversation format."""
    system_message = SystemMessage(content=f"""You are an expert translator of Tibetan Buddhist texts into clear, accessible modern {language}. Your task is to:

1. Create a plain, accessible translation that preserves the meaning but uses simple, straightforward {language}
2. Focus on clarity and readability for modern readers without specialized Buddhist knowledge
3. Make the translation direct and concise while maintaining all key content
4. Use natural, flowing language that would be understood by educated non-specialists

LANGUAGE-SPECIFIC REQUIREMENTS FOR {language.upper()}:
- Your translation MUST be in fluent, natural {language} as spoken by native speakers
- Use appropriate {language} grammar, syntax, and idiomatic expressions
- Maintain proper {language} sentence structure and flow
- Choose words and phrases that sound natural in {language}
- Avoid awkward phrasing, word-for-word translations, or unnatural constructions

Your translation should be accurate but prioritize clarity, naturalness, and accessibility over technical precision.
IMPORTANT: Your translation MUST be in {language} and must sound natural to native {language} speakers.""")
    
    # Start the conversation with the system message
    messages = [system_message]
    
    # Add few-shot examples as a multi-turn conversation
    for example in plain_translation_examples:
        # Human message
        messages.append(HumanMessage(content=f"""Translate this Tibetan Buddhist text into plain, accessible modern {language}:

{example['source']}"""))
        
        # Assistant message (not SystemMessage) with the expected response
        messages.append({"type": "ai", "content": example['plaintext_translation']})
    
    # Add the actual request
    messages.append(HumanMessage(content=f"""Translate this Tibetan Buddhist text into plain, accessible modern {language}:

{source_text}"""))
    
    return messages


def get_zero_shot_commentary_prompt(source_text, language="English"):
    """Generate a zero-shot prompt for creating commentary when no existing commentaries are available."""
    system_message = SystemMessage(content=f"""You are an expert in Tibetan Buddhist philosophy tasked with creating a commentary on Tibetan Buddhist texts. You must write a commentary in {language}. Your task is to:

1. Analyze the source text carefully, line by line
2. Explain the doctrinal significance of each line or phrase
3. Provide context on any Buddhist concepts mentioned
4. Elucidate philosophical implications
5. Clarify technical terminology
6. Consider different interpretative traditions where relevant

Your commentary should be scholarly yet accessible, balancing philological detail with philosophical insight.
IMPORTANT: Your commentary MUST be written in {language}.""")
    
    # For zero-shot, we just create a direct request
    messages = [system_message]
    
    # Add the request
    messages.append(HumanMessage(content=f"""Create a detailed commentary for this Tibetan Buddhist text:

SOURCE TEXT:
{source_text}

Please analyze this text line by line, explaining its meaning, philosophical context, and doctrinal significance in {language}.
"""))
    
    return messages

def create_source_analysis(source_text, sanskrit_text="", language="English"):
    """Create a focused analysis of the source text without speculative commentary."""
    
    # Create prompt for source-focused analysis
    system_message = SystemMessage(content=f"""Analyze this Tibetan Buddhist text directly from the source without speculative commentary. Your task is to:

1. Identify grammatical structures and linguistic patterns in the Tibetan text
2. Note any technical Buddhist terminology and its precise meaning
3. Document structural elements (verse format, paragraph breaks, etc.)
4. Highlight key concepts but avoid interpretive speculation
5. Provide literal meanings while noting potential ambiguities

Focus ONLY on what can be directly determined from the text itself.
IMPORTANT: Your analysis MUST be written in {language}.""")
    
    # Create content with conditional Sanskrit part
    content = f"""Analyze this Tibetan Buddhist text:

SOURCE TEXT:
{source_text}

"""
    # Add Sanskrit text if available
    if sanskrit_text:
        content += f"SANSKRIT TEXT (if available):\n{sanskrit_text}\n\n"
    
    content += f"Please provide a detailed linguistic and structural analysis in {language}, focusing exclusively on the text itself without speculative interpretation."
    
    messages = [system_message, HumanMessage(content=content)]
    
    # Use thinking LLM for careful analysis
    response = llm_thinking.invoke(messages)
    
    # Extract content from thinking response
    analysis_content = ""
    
    if isinstance(response, list):
        # Handle thinking output format, extracting only the text part
        for chunk in response:
            if isinstance(chunk, dict) and chunk.get('type') == 'text':
                analysis_content = chunk.get('text', '')
    elif hasattr(response, 'content'):
        if isinstance(response.content, list) and len(response.content) > 1:
            # Extract text from the second element (typical thinking response structure)
            analysis_content = response.content[1].get('text', '')
        else:
            analysis_content = response.content
    else:
        analysis_content = str(response)
    
    return analysis_content

def get_enhanced_translation_prompt(sanskrit, source, source_analysis, language="English"):
    """Generate an enhanced prompt for fluent yet accurate translation."""
    return f"""
    Translate this Tibetan Buddhist text into natural, eloquent {language}:

    Sanskrit text:
    {sanskrit}

    Source Text:
    {source}

    Source Analysis:
    {source_analysis}

    TRANSLATION PRIORITIES:
    1. FLUENCY: Create text that flows naturally in {language} as if originally composed in it
    2. ACCURACY: Preserve the precise meaning of every term and concept
    3. STRUCTURE: Maintain the original's structural elements while adapting to {language} literary norms
    4. TERMINOLOGY: Use established Buddhist terminology in {language} where it exists

    LANGUAGE-SPECIFIC GUIDANCE FOR {language.upper()}:
    - Restructure sentences to match natural {language} rhythm and flow
    - Use idiomatic expressions native to {language} literary tradition
    - Adapt sentence length and complexity to {language} conventions
    - Choose terminology that resonates with {language}-speaking Buddhist practitioners
    - Balance technical precision with literary elegance

    HANDLING CHALLENGING ELEMENTS:
    - For ambiguous passages: provide the most natural reading but stay close to literal meaning
    - For technical terms: use established translations if they exist, otherwise translate conceptually
    - For cultural references: preserve the original concept while making it accessible to {language} readers
    - For poetic elements: capture the aesthetic quality in {language} poetic conventions
    
    AVOID:
    - Word-for-word translation that creates awkward {language} phrasing
    - Overly simplifying complex concepts
    - Adding interpretive content not present in the source
    - Losing structural elements (verse format, sections, etc.)
    - Using inconsistent terminology for repeated concepts

    YOUR GOAL: A translation that a native {language} speaker with Buddhist knowledge would recognize as both authentic to the tradition and natural in their language.

    Generate only the translation with no explanatory notes.
    """

def get_combined_commentary_prompt(source_text, commentaries, has_commentaries=True, language="English"):
    """Generate a prompt for creating combined commentary, with language-specific examples and instructions."""
    # If there are no commentaries, use zero-shot mode instead
    if not has_commentaries:
        return get_zero_shot_commentary_prompt(source_text, language)
    
    # Create language-specific system message
    if language.lower() == "chinese":
        system_content = """你是一位精通藏传佛教哲学的专家，负责为藏文佛教文本创建综合、整合的注释。你的任务是：

1. 分析同一文本的多个注释，并将它们整合为一个连贯的解释
2. 保留每个注释中的所有关键哲学观点
3. 详细解释源文本的每一行，包括其教义意义
4. 以构建对文本更清晰理解的方式连接这些注释
5. 确保所有佛教术语得到适当解释
6. 你可以使用标题，如"# 顶礼与目的陈述"，但不要使用"# 综合注释"这样的通用标题

你的综合注释应当全面、学术，并对文本提供完整分析。
重要：你的注释必须用中文撰写。"""
    elif language.lower() == "hindi":
        system_content = """आप तिब्बती बौद्ध दर्शन के विशेषज्ञ हैं जिन्हें तिब्बती बौद्ध ग्रंथों पर एक व्यापक, एकीकृत टीका बनाने का कार्य सौंपा गया है। आपका कार्य है:

1. एक ही पाठ पर कई टीकाओं का विश्लेषण करना और उन्हें एक सुसंगत व्याख्या में एकीकृत करना
2. प्रत्येक टीका से सभी प्रमुख दार्शनिक बिंदुओं को संरक्षित करना
3. स्रोत पाठ की प्रत्येक पंक्ति को विस्तार से समझाना, जिसमें उसका धार्मिक महत्व शामिल है
4. टीकाओं को इस तरह से जोड़ना जिससे पाठ की स्पष्ट समझ विकसित हो
5. सुनिश्चित करना कि सभी तकनीकी बौद्ध शब्दावली उचित रूप से समझाई गई है
6. आप शीर्षक का उपयोग कर सकते हैं, लेकिन "# हिंदी में संयुक्त टीका" जैसा सामान्य शीर्षक न उपयोग करें

आपकी संयुक्त टीका व्यापक, विद्वतापूर्ण होनी चाहिए और पाठ का पूर्ण विश्लेषण प्रदान करनी चाहिए।
महत्वपूर्ण: आपकी टीका हिंदी में लिखी होनी चाहिए।"""
    else:  # Default English
        system_content = f"""You are an expert in Tibetan Buddhist philosophy tasked with creating a comprehensive, integrated commentary on Tibetan Buddhist texts. Your task is to:

1. Analyze multiple commentaries on the same text and integrate them into a single cohesive explanation
2. Preserve all key philosophical points from each commentary
3. Explain each line of the source text in detail, including its doctrinal significance
4. Connect the commentaries in a way that builds a clearer understanding of the text
5. Ensure all technical Buddhist terminology is properly explained
6. Avoid at all cost titles like "# Combined Commentary"

Your combined commentary should be thorough, scholarly, and provide a complete analysis of the text.
IMPORTANT: Your commentary MUST be written in {language}."""
    
    system_message = SystemMessage(content=system_content)
    
    # Create few-shot examples as a conversation
    messages = [system_message]
    
    # Filter examples to include ones in the target language
    target_lang_examples = []
    other_lang_examples = []
    
    for example in combined_commentary_examples:
        if example.get('language', 'English').lower() == language.lower():
            target_lang_examples.append(example)
        else:
            other_lang_examples.append(example)
    
    # Ensure we have at least one example in the target language
    examples_to_use = target_lang_examples[:1]  # Take one target language example
    
    # If we don't have any target language examples, use an example from another language
    if not examples_to_use and other_lang_examples:
        examples_to_use = [other_lang_examples[0]]
    
    # Add more target language examples if available, up to a maximum of 2 examples
    if len(target_lang_examples) > 1:
        examples_to_use.extend(target_lang_examples[1:2])
    
    # Add few-shot examples
    for example in examples_to_use:
        # Add user message with request
        messages.append(HumanMessage(content=f"""Create a combined commentary for this Tibetan Buddhist text based on multiple source commentaries:

SOURCE TEXT:
{example['source']}

COMMENTARIES:
{example['commentaries']}
"""))
        
        # Add assistant's correct response as an AI message
        messages.append({"type": "ai", "content": example['combined_commentary']})
    
    # Add the actual request
    messages.append(HumanMessage(content=f"""Create a combined commentary for this Tibetan Buddhist text based on multiple source commentaries:

IMPORTANT: Your commentary MUST be written in {language}.

SOURCE TEXT:
{source_text}

COMMENTARIES:
{commentaries}
"""))
    
    return messages


# Initialize standard LLM instance 
llm = ChatAnthropic(model=LLM_MODEL_NAME, max_tokens=MAX_TOKENS)

# Initialize LLM instance with thinking capability for complex reasoning tasks
llm_thinking = ChatAnthropic(
    model="claude-3-7-sonnet-latest",
    max_tokens=5000,
    thinking={"type": "enabled", "budget_tokens": 2000},
)

def dict_to_text(d, indent=0):
    """Convert dictionary to formatted text."""
    text = ""
    spacing = " " * indent
    
    for key, value in d.items():
        if isinstance(value, dict):
            text += f"{spacing}{key}:\n{dict_to_text(value, indent + 2)}"
        else:
            text += f"{spacing}{key}: {value}\n"
    
    return text

def convert_state_to_jsonl(state_dict: State, file_path: str):
    """Save the state dictionary in JSONL format."""
    with open(file_path, 'a', encoding='utf-8') as f:
        json.dump(state_dict, f, ensure_ascii=False)
        f.write("\n")
def get_json_data(file_path='commentary_1.json'):
    """Load data from a JSON file."""
    logger.debug(f"Loading JSON from file: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as json_file:
            file_content = json_file.read()
            logger.debug(f"Raw file content: {file_content[:200]}...")  # Log first 200 chars
            
            # Log type information before parsing
            logger.debug(f"File content type: {type(file_content)}")
            
            try:
                data = json.loads(file_content)
                logger.debug(f"Parsed data type: {type(data)}")
                
                # If data contains entries, log their structure
                if 'entries' in data:
                    logger.debug(f"Entries type: {type(data['entries'])}")
                    logger.debug(f"First entry sample: {str(data['entries'][0]) if data['entries'] and isinstance(data['entries'], list) else 'No entries or not a list'}")
                
                return data
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {str(e)}")
                logger.error(f"Error position: {e.pos}, line: {e.lineno}, column: {e.colno}")
                logger.error(f"Document snippet at error: {file_content[max(0, e.pos-50):e.pos+50]}")
                raise
    except Exception as e:
        logger.error(f"Error loading JSON file: {str(e)}")
        raise
