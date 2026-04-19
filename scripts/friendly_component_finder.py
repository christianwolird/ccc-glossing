#!/usr/bin/env python3

from collections import defaultdict, deque

PAIR_TEXT = r"""
ABRAHAM <-> PATRIARCH
ABRAHAM <-> COVENANT
ABSOLUTION <-> PENANCE, SACRAMENT OF
ACEDIA <-> SLOTH
ADAM <-> ORIGINAL SIN
ADORATION <-> WORSHIP
ALMSGIVING <-> PENANCE
ANGEL <-> GUARDIAN ANGELS
ANGER <-> CAPITAL SINS
ANNUNCIATION <-> JESUS CHRIST
ANOINTING <-> CHRIST
ANOINTING <-> CHRISMATION
ANOINTING OF THE SICK <-> SACRAMENT
APOSTLE <-> BISHOP
APOSTLE <-> GOSPEL
APOSTLE <-> APOSTOLIC SUCCESSION
APOSTLE <-> MISSION
APOSTLES’ CREED <-> CREED
BAPTISM <-> LIFE
BAPTISM <-> CONFIRMATION
BAPTISM <-> SACRAMENT
BEATITUDES <-> HAPPINESS
BIBLE <-> NEW TESTAMENT
BIBLE <-> SCRIPTURE, SACRED
BIBLE <-> OLD TESTAMENT
BISHOP <-> EPISCOPAL/EPISCOPATE
BLESSED SACRAMENT <-> TABERNACLE
BLESSING <-> CONSECRATION
BODY OF CHRIST <-> CHURCH
CANON OF THE MASS <-> EUCHARISTIC PRAYER
CANONIZATION <-> SAINT
CAPITAL SINS <-> SLOTH
CAPITAL SINS <-> VICE
CAPITAL SINS <-> PRIDE
CAPITAL SINS <-> COVETOUSNESS
CAPITAL SINS <-> GLUTTONY
CAPITAL SINS <-> ENVY
CARDINAL VIRTUES <-> VIRTUE
CATHOLIC <-> CHURCH
CHARISM <-> GRACE
CHARITY <-> LOVE
CHRIST <-> JESUS CHRIST
CHRIST <-> MISSION
CHRIST <-> MESSIAH
CHRISTIAN <-> CHURCH
COMMUNION <-> EUCHARIST
COMMUNION OF SAINTS <-> SAINT
CONFESSION <-> PENANCE, SACRAMENT OF
CONFIRMATION <-> SACRAMENT
CONSCIENCE <-> EXAMINATION OF CONSCIENCE
CONSECRATED LIFE <-> OBEDIENCE
CONSECRATED LIFE <-> POVERTY
CONSECRATED LIFE <-> EVANGELICAL COUNSELS
CONTRITION <-> PENANCE, SACRAMENT OF
COUNCIL, ECUMENICAL <-> ECUMENICAL COUNCIL
COUNSEL <-> GIFTS OF THE HOLY SPIRIT
COUNSEL <-> EVANGELICAL COUNSELS
COVENANT <-> NEW TESTAMENT
COVENANT <-> PROPHET
COVENANT <-> MOSES
COVENANT <-> OLD TESTAMENT
CREED <-> FAITH
CREED <-> NICENE CREED
CROSS <-> SIGN OF THE CROSS
DEACON, DIACONATE <-> DIACONATE
DEACON, DIACONATE <-> MINISTRY
DECALOGUE <-> MOSES
DEMON <-> DEVIL/DEMON
DEPOSIT OF FAITH <-> TRADITION
DEVIL/DEMON <-> EVIL
DEVIL/DEMON <-> SATAN
DIOCESE <-> PARTICULAR CHURCH
DIOCESE <-> EPARCHY
DOXOLOGY <-> PRAISE
EASTER <-> SUNDAY
EASTER <-> HOLY WEEK
EASTER <-> LENT
EREMITICAL LIFE <-> HERMIT
ETERNAL LIFE <-> LIFE
ETERNAL LIFE <-> HEAVEN
EUCHARIST <-> SACRIFICE
EUCHARIST <-> MASS
EUCHARIST <-> INITIATION, CHRISTIAN
EUCHARIST <-> SACRAMENT
EVANGELICAL COUNSELS <-> OBEDIENCE
EVANGELICAL COUNSELS <-> POVERTY
EVANGELIST <-> GOSPEL
EVIL <-> MORALITY
FASTING <-> LENT
FASTING <-> PENANCE
FEAR OF THE LORD <-> GIFTS OF THE HOLY SPIRIT
FORTITUDE <-> GIFTS OF THE HOLY SPIRIT
GIFTS OF THE HOLY SPIRIT <-> WISDOM
GIFTS OF THE HOLY SPIRIT <-> PIETY
GOD <-> REVELATION
GOD <-> SALVATION
GOSPEL <-> TRADITION
GRACE <-> LIFE
GRACE <-> SANCTIFYING GRACE
HAPPINESS <-> PARADISE
HAPPINESS <-> VOCATION
HEAVEN <-> LIFE
HOLY SPIRIT <-> TRINITY
HOLY SPIRIT <-> SPIRIT
HOLY SPIRIT <-> PERSON, DIVINE
HOLY SPIRIT <-> PARACLETE
HOLY WEEK <-> PASSION
HUMILITY <-> POVERTY
IMMORTALITY <-> SOUL
INCARNATION <-> NATURE
INTERCESSION <-> PRAYER
ISRAEL <-> OLD COVENANT
ISRAEL <-> MOSES
JESUS CHRIST <-> VIRGIN MARY
JESUS CHRIST <-> MESSIAH
JESUS CHRIST <-> SON OF GOD
JUDGMENT <-> LAST JUDGMENT
LATIN RITE <-> RITES
LIFE <-> SANCTIFYING GRACE
LORD’S PRAYER <-> OUR FATHER
MAGISTERIUM <-> TEACHING OFFICE
MARRIAGE <-> MATRIMONY
MARY <-> OUR LADY
MERCY <-> WORKS OF MERCY
NATURE <-> ORIGINAL SIN
NEW TESTAMENT <-> TESTAMENT
PAPACY <-> POPE
PARISH <-> PASTOR/PASTORAL OFFICE
PAROUSIA <-> SECOND COMING OF CHRIST
PASCH/PASCHAL LAMB <-> PASSOVER
PENANCE <-> PENITENT/PENITENTIAL
PENANCE, SACRAMENT OF <-> PENITENT/PENITENTIAL
PENITENT/PENITENTIAL <-> SATISFACTION (FOR SIN)
PERSON, DIVINE <-> TRINITY
POPE <-> PRIMACY
PRAISE <-> PRAYER
PRESBYTER <-> PRIESTHOOD
PRIESTHOOD <-> PRIESTHOOD OF CHRIST
RELIGION <-> WORSHIP
REPARATION <-> SATISFACTION (FOR SIN)
SIN <-> VENIAL SIN
VIRTUE <-> VIRTUES, THEOLOGICAL
""".strip()


def parse_edges(text: str) -> list[tuple[str, str]]:
    edges = []
    for lineno, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        if "<->" not in line:
            raise ValueError(f"Line {lineno} is missing '<->': {raw_line!r}")
        left, right = line.split("<->", maxsplit=1)
        u = left.strip()
        v = right.strip()
        if not u or not v:
            raise ValueError(f"Line {lineno} has an empty endpoint: {raw_line!r}")
        edges.append((u, v))
    return edges


def build_graph(edges: list[tuple[str, str]]) -> dict[str, set[str]]:
    graph: dict[str, set[str]] = defaultdict(set)
    for u, v in edges:
        graph[u].add(v)
        graph[v].add(u)
    return graph


def connected_components(graph: dict[str, set[str]]) -> list[set[str]]:
    seen: set[str] = set()
    components: list[set[str]] = []

    for start in graph:
        if start in seen:
            continue

        comp: set[str] = set()
        queue = deque([start])
        seen.add(start)

        while queue:
            u = queue.popleft()
            comp.add(u)
            for v in graph[u]:
                if v not in seen:
                    seen.add(v)
                    queue.append(v)

        components.append(comp)

    return components


def component_edges(
    component: set[str],
    edges: list[tuple[str, str]],
) -> list[tuple[str, str]]:
    out = []
    for u, v in edges:
        if u in component and v in component:
            a, b = sorted((u, v))
            out.append((a, b))
    return sorted(set(out))


def main() -> None:
    edges = parse_edges(PAIR_TEXT)
    graph = build_graph(edges)
    components = connected_components(graph)

    largest = max(components, key=len)
    largest_edges = component_edges(largest, edges)

    print(f"Number of vertices in graph: {len(graph)}")
    print(f"Number of edges in graph: {len(edges)}")
    print(f"Number of connected components: {len(components)}")
    print()
    print(f"Largest component size: {len(largest)}")
    print("Vertices:")
    for vertex in sorted(largest):
        print(f"  {vertex}")
    print()
    print(f"Edges in largest component: {len(largest_edges)}")
    for u, v in largest_edges:
        print(f"  {u} <-> {v}")


if __name__ == "__main__":
    main()
