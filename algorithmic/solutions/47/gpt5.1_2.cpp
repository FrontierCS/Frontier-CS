#include <iostream>
#include <vector>
#include <string>
#include <cctype>
#include <cmath>
#include <algorithm>
#include <iterator>

using namespace std;

struct ItemType {
    string type;
    int w, h;
    long long v;
    int limit;
};

struct Placement {
    string type;
    int x, y;
    int rot;
};

string inputData;
size_t posIdx = 0;

int binW = 0, binH = 0;
bool allowRotate = false;
vector<ItemType> items;

// Parsing helpers
void skipWS() {
    while (posIdx < inputData.size() && isspace((unsigned char)inputData[posIdx])) posIdx++;
}

char peekChar() {
    if (posIdx >= inputData.size()) return '\0';
    return inputData[posIdx];
}

char getChar() {
    if (posIdx >= inputData.size()) return '\0';
    return inputData[posIdx++];
}

string parseString() {
    skipWS();
    string res;
    if (getChar() != '"') return res;
    while (posIdx < inputData.size()) {
        char c = getChar();
        if (c == '"') break;
        if (c == '\\') {
            if (posIdx >= inputData.size()) break;
            char esc = getChar();
            switch (esc) {
                case '"': case '\\': case '/':
                    res.push_back(esc);
                    break;
                case 'b':
                    res.push_back('\b');
                    break;
                case 'f':
                    res.push_back('\f');
                    break;
                case 'n':
                    res.push_back('\n');
                    break;
                case 'r':
                    res.push_back('\r');
                    break;
                case 't':
                    res.push_back('\t');
                    break;
                case 'u': {
                    // Skip 4 hex digits, output placeholder
                    for (int i = 0; i < 4 && posIdx < inputData.size(); ++i) posIdx++;
                    res.push_back('?');
                    break;
                }
                default:
                    res.push_back(esc);
                    break;
            }
        } else {
            res.push_back(c);
        }
    }
    return res;
}

long long parseInt64() {
    skipWS();
    bool neg = false;
    if (peekChar() == '-') {
        neg = true;
        getChar();
    }
    long long x = 0;
    while (isdigit((unsigned char)peekChar())) {
        x = x * 10 + (getChar() - '0');
    }
    return neg ? -x : x;
}

bool parseBool() {
    skipWS();
    if (inputData.compare(posIdx, 4, "true") == 0) {
        posIdx += 4;
        return true;
    } else if (inputData.compare(posIdx, 5, "false") == 0) {
        posIdx += 5;
        return false;
    } else {
        // Fallback: consume alphabetic token
        while (posIdx < inputData.size() && isalpha((unsigned char)inputData[posIdx])) posIdx++;
        return false;
    }
}

void parseNull() {
    skipWS();
    if (inputData.compare(posIdx, 4, "null") == 0) {
        posIdx += 4;
    } else {
        while (posIdx < inputData.size() && isalpha((unsigned char)inputData[posIdx])) posIdx++;
    }
}

void skipValue();

void skipObject() {
    skipWS();
    if (peekChar() != '{') return;
    getChar();
    while (true) {
        skipWS();
        if (peekChar() == '}') {
            getChar();
            break;
        }
        parseString(); // key
        skipWS();
        if (peekChar() == ':') getChar();
        skipValue();
        skipWS();
        if (peekChar() == ',') {
            getChar();
            continue;
        } else if (peekChar() == '}') {
            continue;
        } else {
            break;
        }
    }
}

void skipArray() {
    skipWS();
    if (peekChar() != '[') return;
    getChar();
    while (true) {
        skipWS();
        if (peekChar() == ']') {
            getChar();
            break;
        }
        skipValue();
        skipWS();
        if (peekChar() == ',') {
            getChar();
            continue;
        } else if (peekChar() == ']') {
            continue;
        } else {
            break;
        }
    }
}

void skipValue() {
    skipWS();
    char c = peekChar();
    if (c == '{') {
        skipObject();
    } else if (c == '[') {
        skipArray();
    } else if (c == '"') {
        (void)parseString();
    } else if (c == 't' || c == 'f') {
        (void)parseBool();
    } else if (c == 'n') {
        parseNull();
    } else {
        (void)parseInt64();
    }
}

void parseBinObject() {
    skipWS();
    if (peekChar() != '{') return;
    getChar();
    while (true) {
        skipWS();
        if (peekChar() == '}') {
            getChar();
            break;
        }
        string key = parseString();
        skipWS();
        if (peekChar() == ':') getChar();
        if (key == "W") {
            binW = (int)parseInt64();
        } else if (key == "H") {
            binH = (int)parseInt64();
        } else if (key == "allow_rotate") {
            allowRotate = parseBool();
        } else {
            skipValue();
        }
        skipWS();
        if (peekChar() == ',') {
            getChar();
            continue;
        } else if (peekChar() == '}') {
            continue;
        } else {
            break;
        }
    }
}

void parseItemObject() {
    skipWS();
    if (peekChar() != '{') return;
    getChar();
    ItemType it;
    it.w = it.h = 0;
    it.v = 0;
    it.limit = 0;
    while (true) {
        skipWS();
        if (peekChar() == '}') {
            getChar();
            break;
        }
        string key = parseString();
        skipWS();
        if (peekChar() == ':') getChar();
        if (key == "type") {
            it.type = parseString();
        } else if (key == "w") {
            it.w = (int)parseInt64();
        } else if (key == "h") {
            it.h = (int)parseInt64();
        } else if (key == "v") {
            it.v = parseInt64();
        } else if (key == "limit") {
            it.limit = (int)parseInt64();
        } else {
            skipValue();
        }
        skipWS();
        if (peekChar() == ',') {
            getChar();
            continue;
        } else if (peekChar() == '}') {
            continue;
        } else {
            break;
        }
    }
    items.push_back(it);
}

void parseItemsArray() {
    skipWS();
    if (peekChar() != '[') return;
    getChar();
    while (true) {
        skipWS();
        if (peekChar() == ']') {
            getChar();
            break;
        }
        parseItemObject();
        skipWS();
        if (peekChar() == ',') {
            getChar();
            continue;
        } else if (peekChar() == ']') {
            continue;
        } else {
            break;
        }
    }
}

void parseTopLevel() {
    skipWS();
    if (peekChar() != '{') return;
    getChar();
    while (true) {
        skipWS();
        if (peekChar() == '}') {
            getChar();
            break;
        }
        string key = parseString();
        skipWS();
        if (peekChar() == ':') getChar();
        if (key == "bin") {
            parseBinObject();
        } else if (key == "items") {
            parseItemsArray();
        } else {
            skipValue();
        }
        skipWS();
        if (peekChar() == ',') {
            getChar();
            continue;
        } else if (peekChar() == '}') {
            continue;
        } else {
            break;
        }
    }
}

// Packing heuristic: horizontal shelves, greedy by value density
vector<Placement> packShelf() {
    vector<Placement> placements;
    int M = (int)items.size();
    vector<int> remaining(M);
    for (int i = 0; i < M; ++i) remaining[i] = items[i].limit;

    int currentY = 0;
    const double EPS = 1e-12;

    while (currentY < binH) {
        int rowY = currentY;
        int rowHeight = 0;
        int x = 0;
        bool placedAny = false;

        while (x < binW) {
            int remW = binW - x;
            int remH = binH - rowY;

            int bestT = -1;
            int bestRot = 0;
            int bestW = 0, bestH = 0;
            double bestDensity = -1.0;

            for (int t = 0; t < M; ++t) {
                if (remaining[t] <= 0) continue;
                // orientation 0
                {
                    int w = items[t].w;
                    int h = items[t].h;
                    if (w <= remW && h <= remH) {
                        double density = (double)items[t].v / (double)(w * (double)h);
                        bool better = false;
                        if (density > bestDensity + EPS) {
                            better = true;
                        } else if (fabs(density - bestDensity) <= EPS) {
                            if (bestT == -1 || h < bestH) {
                                better = true;
                            } else if (h == bestH) {
                                int diff = std::abs(remW - w);
                                int bestDiff = std::abs(remW - bestW);
                                if (diff < bestDiff) better = true;
                            }
                        }
                        if (better) {
                            bestT = t;
                            bestRot = 0;
                            bestW = w;
                            bestH = h;
                            bestDensity = density;
                        }
                    }
                }
                // orientation 1 if allowed
                if (allowRotate) {
                    int w = items[t].h;
                    int h = items[t].w;
                    if (w <= remW && h <= remH) {
                        double density = (double)items[t].v / (double)(w * (double)h);
                        bool better = false;
                        if (density > bestDensity + EPS) {
                            better = true;
                        } else if (fabs(density - bestDensity) <= EPS) {
                            if (bestT == -1 || h < bestH) {
                                better = true;
                            } else if (h == bestH) {
                                int diff = std::abs(remW - w);
                                int bestDiff = std::abs(remW - bestW);
                                if (diff < bestDiff) better = true;
                            }
                        }
                        if (better) {
                            bestT = t;
                            bestRot = 1;
                            bestW = w;
                            bestH = h;
                            bestDensity = density;
                        }
                    }
                }
            }

            if (bestT == -1) break; // no item fits at this x in this row

            Placement p;
            p.type = items[bestT].type;
            p.x = x;
            p.y = rowY;
            p.rot = allowRotate ? bestRot : 0;
            placements.push_back(p);

            x += bestW;
            if (bestH > rowHeight) rowHeight = bestH;
            remaining[bestT]--;
            placedAny = true;
        }

        if (!placedAny) break;
        currentY += rowHeight;
        if (rowHeight <= 0) break; // safety
    }

    return placements;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    inputData.assign((istreambuf_iterator<char>(cin)), istreambuf_iterator<char>());
    posIdx = 0;
    parseTopLevel();

    vector<Placement> placements = packShelf();

    cout << "{\n  \"placements\": [\n";
    for (size_t i = 0; i < placements.size(); ++i) {
        const auto &p = placements[i];
        cout << "    {\"type\":\"" << p.type << "\",\"x\":" << p.x
             << ",\"y\":" << p.y << ",\"rot\":" << p.rot << "}";
        if (i + 1 < placements.size()) cout << ",\n";
        else cout << "\n";
    }
    cout << "  ]\n}\n";

    return 0;
}