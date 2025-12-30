#include <bits/stdc++.h>
using namespace std;

struct Item {
    string type;
    int w, h, v, limit;
};

struct FreeRect {
    int x, y, w, h;
};

struct Placement {
    string type;
    int x, y, rot;
};

string input_str;
int posi;
int W, H;
bool allow_rotate;
vector<Item> items;

void skip() {
    while (posi < input_str.size() && isspace(input_str[posi])) posi++;
}

bool expect_char(char c) {
    skip();
    if (posi >= input_str.size() || input_str[posi] != c) return false;
    posi++;
    return true;
}

string expect_key(const string& key) {
    skip();
    string found;
    for (char ch : key) {
        if (posi >= input_str.size() || input_str[posi] != ch) return "";
        found += input_str[posi++];
    }
    return found;
}

int parse_int() {
    skip();
    int sign = 1;
    if (posi < input_str.size() && input_str[posi] == '-') {
        sign = -1;
        posi++;
    }
    int num = 0;
    while (posi < input_str.size() && isdigit(input_str[posi])) {
        num = num * 10 + (input_str[posi++] - '0');
    }
    return sign * num;
}

string parse_string() {
    skip();
    if (posi >= input_str.size() || input_str[posi] != '"') return "";
    posi++;
    string res;
    while (posi < input_str.size() && input_str[posi] != '"') {
        res += input_str[posi++];
    }
    if (posi < input_str.size() && input_str[posi] == '"') posi++;
    return res;
}

bool parse_bool() {
    skip();
    if (posi + 4 <= input_str.size() && input_str.substr(posi, 4) == "true") {
        posi += 4;
        return true;
    } else if (posi + 5 <= input_str.size() && input_str.substr(posi, 5) == "false") {
        posi += 5;
        return false;
    }
    return false;
}

int main() {
    input_str.assign(istreambuf_iterator<char>(cin), istreambuf_iterator<char>());
    posi = 0;

    // Parse bin
    skip();
    expect_char('{');
    skip();
    expect_key("\"bin\"");
    expect_char(':');
    skip();
    expect_char('{');
    skip();
    expect_key("\"W\"");
    expect_char(':');
    W = parse_int();
    skip();
    expect_char(',');
    skip();
    expect_key("\"H\"");
    expect_char(':');
    H = parse_int();
    skip();
    expect_char(',');
    skip();
    expect_key("\"allow_rotate\"");
    expect_char(':');
    allow_rotate = parse_bool();
    skip();
    expect_char('}');

    // Parse items
    skip();
    expect_char(',');
    skip();
    expect_key("\"items\"");
    expect_char(':');
    skip();
    expect_char('[');
    while (true) {
        skip();
        if (expect_char(']')) break;
        expect_char('{');
        skip();
        expect_key("\"type\"");
        expect_char(':');
        skip();
        Item it;
        it.type = parse_string();
        skip();
        expect_char(',');
        skip();
        expect_key("\"w\"");
        expect_char(':');
        skip();
        it.w = parse_int();
        skip();
        expect_char(',');
        skip();
        expect_key("\"h\"");
        expect_char(':');
        skip();
        it.h = parse_int();
        skip();
        expect_char(',');
        skip();
        expect_key("\"v\"");
        expect_char(':');
        skip();
        it.v = parse_int();
        skip();
        expect_char(',');
        skip();
        expect_key("\"limit\"");
        expect_char(':');
        skip();
        it.limit = parse_int();
        skip();
        expect_char('}');
        items.push_back(it);
        skip();
        if (input_str[posi] == ',') {
            posi++;
        }
    }
    skip();
    expect_char('}');

    int M = items.size();
    vector<double> density(M);
    for (int i = 0; i < M; i++) {
        density[i] = items[i].v / (double(items[i].w) * items[i].h);
    }
    vector<int> order(M);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b) {
        return density[a] > density[b] || (density[a] == density[b] && items[a].v > items[b].v);
    });

    vector<FreeRect> free_rects;
    free_rects.push_back({0, 0, W, H});
    vector<Placement> placements;
    vector<int> used_cnt(M, 0);

    for (int oi = 0; oi < M; oi++) {
        int idx = order[oi];
        Item& it = items[idx];
        int lim = it.limit;
        for (int c = 0; c < lim; c++) {
            int best_fi = -1;
            int best_rot = -1;
            int best_py = INT_MAX;
            int best_px = INT_MAX;
            for (int fi = 0; fi < free_rects.size(); fi++) {
                FreeRect fr = free_rects[fi];
                // rot 0
                {
                    int tro = 0;
                    int ww = it.w;
                    int hh = it.h;
                    if (ww <= fr.w && hh <= fr.h) {
                        int ty = fr.y;
                        int tx = fr.x;
                        bool update = (ty < best_py) ||
                                      (ty == best_py && tx < best_px) ||
                                      (ty == best_py && tx == best_px && (best_fi == -1 || tro < best_rot));
                        if (update) {
                            best_py = ty;
                            best_px = tx;
                            best_fi = fi;
                            best_rot = tro;
                        }
                    }
                }
                // rot 1
                if (allow_rotate && it.w != it.h) {
                    int tro = 1;
                    int ww = it.h;
                    int hh = it.w;
                    if (ww <= fr.w && hh <= fr.h) {
                        int ty = fr.y;
                        int tx = fr.x;
                        bool update = (ty < best_py) ||
                                      (ty == best_py && tx < best_px) ||
                                      (ty == best_py && tx == best_px && (best_fi == -1 || tro < best_rot));
                        if (update) {
                            best_py = ty;
                            best_px = tx;
                            best_fi = fi;
                            best_rot = tro;
                        }
                    }
                }
            }
            if (best_fi == -1) break;
            FreeRect fr = free_rects[best_fi];
            int ww = (best_rot == 1 ? it.h : it.w);
            int hh = (best_rot == 1 ? it.w : it.h);
            placements.push_back({it.type, fr.x, fr.y, best_rot});
            used_cnt[idx]++;
            // Remove
            free_rects[best_fi] = free_rects.back();
            free_rects.pop_back();
            // Add splits
            int rw = fr.w - ww;
            int th = fr.h - hh;
            if (rw > 0) {
                free_rects.push_back({fr.x + ww, fr.y, rw, hh});
            }
            if (th > 0) {
                free_rects.push_back({fr.x, fr.y + hh, ww, th});
            }
            if (rw > 0 && th > 0) {
                free_rects.push_back({fr.x + ww, fr.y + hh, rw, th});
            }
        }
    }

    // Output
    cout << "{" << endl;
    cout << "  \"placements\": [" << endl;
    for (size_t i = 0; i < placements.size(); ++i) {
        if (i > 0) cout << "," << endl;
        const auto& p = placements[i];
        cout << "    {\"type\":\"" << p.type << "\",\"x\":" << p.x << ",\"y\":" << p.y << ",\"rot\":" << p.rot << "}";
    }
    cout << endl << "  ]" << endl;
    cout << "}" << endl;
    return 0;
}