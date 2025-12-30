#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <map>
#include <ctime>
#include <cmath>
#include <random>

using namespace std;

// --- JSON Parsing Utils ---

struct JsonValue {
    enum Type { J_NULL, J_BOOL, J_INT, J_STRING, J_ARRAY, J_OBJECT };
    Type type = J_NULL;
    bool b_val = false;
    long long i_val = 0;
    string s_val;
    vector<JsonValue> a_val;
    map<string, JsonValue> o_val;
};

class JsonParser {
    string src;
    size_t pos = 0;

    void skipWhitespace() {
        while (pos < src.size() && (src[pos] == ' ' || src[pos] == '\n' || src[pos] == '\r' || src[pos] == '\t')) {
            pos++;
        }
    }

    char peek() {
        skipWhitespace();
        if (pos >= src.size()) return 0;
        return src[pos];
    }

    char consume() {
        char c = peek();
        if (pos < src.size()) pos++;
        return c;
    }

    bool expect(char c) {
        if (peek() == c) {
            pos++;
            return true;
        }
        return false;
    }

    string parseString() {
        expect('"');
        string res;
        while (pos < src.size() && src[pos] != '"') {
            if (src[pos] == '\\') {
                pos++;
                if (pos >= src.size()) break;
                if (src[pos] == 'n') res += '\n';
                else if (src[pos] == 't') res += '\t';
                else res += src[pos];
            } else {
                res += src[pos];
            }
            pos++;
        }
        expect('"');
        return res;
    }

    long long parseInt() {
        size_t start = pos;
        if (pos < src.size() && src[pos] == '-') pos++;
        while (pos < src.size() && isdigit(src[pos])) pos++;
        return stoll(src.substr(start, pos - start));
    }

    bool parseBool() {
        if (src.compare(pos, 4, "true") == 0) {
            pos += 4;
            return true;
        }
        if (src.compare(pos, 5, "false") == 0) {
            pos += 5;
            return false;
        }
        return false;
    }

public:
    JsonValue parse(const string& s) {
        src = s;
        pos = 0;
        return parseValue();
    }

    JsonValue parseValue() {
        char c = peek();
        JsonValue v;
        if (c == '{') {
            v.type = JsonValue::J_OBJECT;
            consume();
            while (peek() != '}') {
                string key = parseString();
                expect(':');
                v.o_val[key] = parseValue();
                if (!expect(',')) break;
            }
            expect('}');
        } else if (c == '[') {
            v.type = JsonValue::J_ARRAY;
            consume();
            while (peek() != ']') {
                v.a_val.push_back(parseValue());
                if (!expect(',')) break;
            }
            expect(']');
        } else if (c == '"') {
            v.type = JsonValue::J_STRING;
            v.s_val = parseString();
        } else if (isdigit(c) || c == '-') {
            v.type = JsonValue::J_INT;
            v.i_val = parseInt();
        } else if (c == 't' || c == 'f') {
            v.type = JsonValue::J_BOOL;
            v.b_val = parseBool();
        }
        return v;
    }
};

// --- Problem Structures ---

struct ItemType {
    string id;
    int w, h, limit;
    long long v;
};

struct Bin {
    int W, H;
    bool allow_rotate;
};

struct Placement {
    string type;
    int x, y, rot;
};

struct Rect {
    int x, y, w, h;
};

struct Piece {
    int type_idx;
    int w, h;
    long long v;
    double density;
};

// --- Solver ---

Bin bin;
vector<ItemType> item_types;

struct Solution {
    vector<Placement> placements;
    long long total_value = 0;
};

bool isContained(const Rect& a, const Rect& b) {
    return a.x >= b.x && a.y >= b.y && a.x + a.w <= b.x + b.w && a.y + a.h <= b.y + b.h;
}

bool intersect(const Rect& a, const Rect& b) {
    return max(a.x, b.x) < min(a.x + a.w, b.x + b.w) &&
           max(a.y, b.y) < min(a.y + a.h, b.y + b.h);
}

Solution solve() {
    vector<Piece> pieces;
    for (int i = 0; i < (int)item_types.size(); ++i) {
        for (int k = 0; k < item_types[i].limit; ++k) {
            pieces.push_back({i, item_types[i].w, item_types[i].h, item_types[i].v, (double)item_types[i].v / (item_types[i].w * item_types[i].h)});
        }
    }

    Solution best_sol;
    best_sol.total_value = -1;

    mt19937 rng(1337);
    clock_t start_time = clock();
    
    // Initial sort
    sort(pieces.begin(), pieces.end(), [](const Piece& a, const Piece& b) {
        if (abs(a.density - b.density) > 1e-9) return a.density > b.density;
        return a.v > b.v;
    });

    int iter = 0;
    while (true) {
        // Time check
        if ((double)(clock() - start_time) / CLOCKS_PER_SEC > 0.96) break;
        iter++;

        vector<Piece> current_pieces = pieces;
        if (iter > 1) {
            // Random perturbation for diversity
            for (auto& p : current_pieces) {
                double noise = uniform_real_distribution<double>(0.95, 1.05)(rng);
                p.density *= noise;
            }
            sort(current_pieces.begin(), current_pieces.end(), [](const Piece& a, const Piece& b) {
                return a.density > b.density;
            });
        }

        // Maximal Rectangles Packing
        vector<Rect> free_rects;
        free_rects.push_back({0, 0, bin.W, bin.H});

        Solution curr_sol;
        
        for (const auto& p : current_pieces) {
            if ((double)(clock() - start_time) / CLOCKS_PER_SEC > 0.98) break;

            int best_rect_idx = -1;
            int best_rot = -1;
            int best_x = -1, best_y = -1;
            
            // Heuristic metrics
            long long best_cost_1 = -1; // Short side residue (minimize)
            long long best_cost_2 = -1; // Long side residue (minimize)
            long long best_cost_3 = -1; // Y coordinate (minimize)
            long long best_cost_4 = -1; // X coordinate (minimize)

            vector<pair<int, int>> dims;
            dims.push_back({p.w, p.h});
            if (bin.allow_rotate && p.w != p.h) dims.push_back({p.h, p.w});

            for (int r = 0; r < (int)dims.size(); ++r) {
                int pw = dims[r].first;
                int ph = dims[r].second;

                for (int i = 0; i < (int)free_rects.size(); ++i) {
                    const Rect& fr = free_rects[i];
                    if (fr.w >= pw && fr.h >= ph) {
                        // Calculate fit quality: Best Short Side Fit
                        int rem_w = fr.w - pw;
                        int rem_h = fr.h - ph;
                        int short_s = min(rem_w, rem_h);
                        int long_s = max(rem_w, rem_h);

                        bool better = false;
                        if (best_rect_idx == -1) better = true;
                        else {
                            if (short_s < best_cost_1) better = true;
                            else if (short_s == best_cost_1) {
                                if (long_s < best_cost_2) better = true;
                                else if (long_s == best_cost_2) {
                                    if (fr.y < best_cost_3) better = true;
                                    else if (fr.y == best_cost_3) {
                                        if (fr.x < best_cost_4) better = true;
                                    }
                                }
                            }
                        }

                        if (better) {
                            best_rect_idx = i;
                            best_rot = (p.w == p.h) ? 0 : r;
                            if (bin.allow_rotate && p.w != p.h && r == 1) best_rot = 1; 
                            else best_rot = 0;

                            best_cost_1 = short_s;
                            best_cost_2 = long_s;
                            best_cost_3 = fr.y;
                            best_cost_4 = fr.x;
                            best_x = fr.x;
                            best_y = fr.y;
                        }
                    }
                }
            }

            if (best_rect_idx != -1) {
                int place_w = (best_rot == 0) ? p.w : p.h;
                int place_h = (best_rot == 0) ? p.h : p.w;
                
                Rect placed_rect = {best_x, best_y, place_w, place_h};
                curr_sol.placements.push_back({item_types[p.type_idx].id, best_x, best_y, best_rot});
                curr_sol.total_value += p.v;

                // Update free rectangles
                vector<Rect> next_free;
                next_free.reserve(free_rects.size());
                
                for (const auto& fr : free_rects) {
                    if (!intersect(fr, placed_rect)) {
                        next_free.push_back(fr);
                    } else {
                        if (placed_rect.y + placed_rect.h < fr.y + fr.h)
                            next_free.push_back({fr.x, placed_rect.y + placed_rect.h, fr.w, fr.y + fr.h - (placed_rect.y + placed_rect.h)});
                        if (placed_rect.y > fr.y)
                            next_free.push_back({fr.x, fr.y, fr.w, placed_rect.y - fr.y});
                        if (placed_rect.x > fr.x)
                            next_free.push_back({fr.x, fr.y, placed_rect.x - fr.x, fr.h});
                        if (placed_rect.x + placed_rect.w < fr.x + fr.w)
                            next_free.push_back({placed_rect.x + placed_rect.w, fr.y, fr.x + fr.w - (placed_rect.x + placed_rect.w), fr.h});
                    }
                }

                // Filter contained rectangles
                vector<Rect> result_free;
                result_free.reserve(next_free.size());
                for (int i = 0; i < (int)next_free.size(); ++i) {
                    bool contained = false;
                    for (int j = 0; j < (int)next_free.size(); ++j) {
                        if (i == j) continue;
                        if (isContained(next_free[i], next_free[j])) {
                            contained = true;
                            break;
                        }
                    }
                    if (!contained) result_free.push_back(next_free[i]);
                }
                free_rects = result_free;
            }
        }

        if (curr_sol.total_value > best_sol.total_value) {
            best_sol = curr_sol;
        }
    }

    return best_sol;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    string input_str, line;
    while (getline(cin, line)) {
        input_str += line + "\n";
    }

    if (input_str.empty()) return 0;

    JsonParser parser;
    JsonValue root = parser.parse(input_str);

    JsonValue j_bin = root.o_val["bin"];
    bin.W = (int)j_bin.o_val["W"].i_val;
    bin.H = (int)j_bin.o_val["H"].i_val;
    bin.allow_rotate = j_bin.o_val["allow_rotate"].b_val;

    JsonValue j_items = root.o_val["items"];
    for (const auto& item : j_items.a_val) {
        ItemType t;
        t.id = item.o_val.at("type").s_val;
        t.w = (int)item.o_val.at("w").i_val;
        t.h = (int)item.o_val.at("h").i_val;
        t.v = item.o_val.at("v").i_val;
        t.limit = (int)item.o_val.at("limit").i_val;
        item_types.push_back(t);
    }

    Solution sol = solve();

    cout << "{\"placements\":[";
    for (size_t i = 0; i < sol.placements.size(); ++i) {
        const auto& p = sol.placements[i];
        cout << "{\"type\":\"" << p.type << "\","
             << "\"x\":" << p.x << ","
             << "\"y\":" << p.y << ","
             << "\"rot\":" << p.rot << "}";
        if (i < sol.placements.size() - 1) cout << ",";
    }
    cout << "]}" << endl;

    return 0;
}