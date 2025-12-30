#include <bits/stdc++.h>
using namespace std;

struct Item {
    string type;
    int w, h, v, limit;
};

struct Placement {
    string type;
    int x, y, rot;
};

struct FreeRect {
    int x, y, w, h;
};

int main() {
    string input_str;
    string line;
    while (getline(cin, line)) {
        input_str += line + "\n";
    }
    string input;
    for (char c : input_str) {
        if (!isspace(c)) input += c;
    }

    // Parse bin
    struct Bin {
        int W, H;
        bool allow_rotate;
    } bin;
    size_t pos = input.find("\"bin\":{");
    if (pos != string::npos) {
        pos += 7;
        // W
        size_t w_pos = input.find("\"W\":", pos);
        if (w_pos != string::npos) {
            w_pos += 5;
            size_t w_end = w_pos;
            while (w_end < input.size() && isdigit(input[w_end])) w_end++;
            bin.W = stoi(input.substr(w_pos, w_end - w_pos));
        }
        // H
        size_t h_pos = input.find("\"H\":", w_end);
        if (h_pos != string::npos) {
            h_pos += 5;
            size_t h_end = h_pos;
            while (h_end < input.size() && isdigit(input[h_end])) h_end++;
            bin.H = stoi(input.substr(h_pos, h_end - h_pos));
        }
        // allow_rotate
        size_t r_pos = input.find("\"allow_rotate\":", h_end);
        if (r_pos != string::npos) {
            r_pos += 16;
            if (r_pos + 4 <= input.size() && input.substr(r_pos, 4) == "true") {
                bin.allow_rotate = true;
            } else {
                bin.allow_rotate = false;
            }
        }
    }

    // Parse items
    vector<Item> items;
    size_t items_start = input.find("\"items\":[");
    if (items_start != string::npos) {
        items_start += 9;
        while (items_start < input.size() && input[items_start] != ']') {
            if (input[items_start] == ',') items_start++;
            if (input[items_start] != '{') {
                items_start++;
                continue;
            }
            items_start++; // skip {
            Item it;
            // type
            size_t t_start = input.find("\"type\":\"", items_start);
            if (t_start != string::npos) {
                t_start += 8;
                size_t t_end = input.find("\"", t_start);
                if (t_end != string::npos) {
                    it.type = input.substr(t_start, t_end - t_start);
                }
            }
            // w
            size_t ww_start = input.find("\"w\":", t_start ? t_start : items_start);
            if (ww_start != string::npos) {
                ww_start += 5;
                size_t ww_end = ww_start;
                while (ww_end < input.size() && isdigit(input[ww_end])) ww_end++;
                it.w = stoi(input.substr(ww_start, ww_end - ww_start));
            }
            // h
            size_t hh_start = input.find("\"h\":", ww_end ? ww_end : items_start);
            if (hh_start != string::npos) {
                hh_start += 5;
                size_t hh_end = hh_start;
                while (hh_end < input.size() && isdigit(input[hh_end])) hh_end++;
                it.h = stoi(input.substr(hh_start, hh_end - hh_start));
            }
            // v
            size_t vv_start = input.find("\"v\":", hh_end ? hh_end : items_start);
            if (vv_start != string::npos) {
                vv_start += 5;
                size_t vv_end = vv_start;
                while (vv_end < input.size() && isdigit(input[vv_end])) vv_end++;
                it.v = stoi(input.substr(vv_start, vv_end - vv_start));
            }
            // limit
            size_t ll_start = input.find("\"limit\":", vv_end ? vv_end : items_start);
            if (ll_start != string::npos) {
                ll_start += 8;
                size_t ll_end = ll_start;
                while (ll_end < input.size() && isdigit(input[ll_end])) ll_end++;
                it.limit = stoi(input.substr(ll_start, ll_end - ll_start));
            }
            // find next
            size_t brace_pos = input.find("}", items_start);
            if (brace_pos != string::npos) {
                items_start = brace_pos + 1;
                items.push_back(it);
            } else {
                break;
            }
        }
    }

    int M = items.size();

    // Sort order by density desc
    vector<int> order(M);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b) {
        long long area_a = (long long)items[a].w * items[a].h;
        long long area_b = (long long)items[b].w * items[b].h;
        double da = (double)items[a].v / area_a;
        double db = (double)items[b].v / area_b;
        return da > db;
    });

    // Remaining limits
    vector<int> remaining(M);
    for (int i = 0; i < M; i++) {
        remaining[i] = items[i].limit;
    }

    // Free rects
    vector<FreeRect> frees;
    frees.push_back({0, 0, bin.W, bin.H});

    // Placements
    vector<Placement> placements;

    // Greedy placement
    for (int oi = 0; oi < M; oi++) {
        int t = order[oi];
        while (remaining[t] > 0) {
            bool placed = false;
            // Try rot 0
            {
                int wp = items[t].w;
                int hp = items[t].h;
                for (size_t i = 0; i < frees.size() && !placed; i++) {
                    FreeRect f = frees[i];
                    if (wp <= f.w && hp <= f.h) {
                        placements.push_back({items[t].type, f.x, f.y, 0});
                        remaining[t]--;
                        frees.erase(frees.begin() + i);
                        if (f.w - wp > 0) {
                            frees.push_back({f.x + wp, f.y, f.w - wp, f.h});
                        }
                        if (f.h - hp > 0) {
                            frees.push_back({f.x, f.y + hp, wp, f.h - hp});
                        }
                        placed = true;
                    }
                }
            }
            // Try rot 1 if allowed and not placed
            if (!placed && bin.allow_rotate) {
                int wp = items[t].h;
                int hp = items[t].w;
                for (size_t i = 0; i < frees.size() && !placed; i++) {
                    FreeRect f = frees[i];
                    if (wp <= f.w && hp <= f.h) {
                        placements.push_back({items[t].type, f.x, f.y, 1});
                        remaining[t]--;
                        frees.erase(frees.begin() + i);
                        if (f.w - wp > 0) {
                            frees.push_back({f.x + wp, f.y, f.w - wp, f.h});
                        }
                        if (f.h - hp > 0) {
                            frees.push_back({f.x, f.y + hp, wp, f.h - hp});
                        }
                        placed = true;
                    }
                }
            }
            if (!placed) break;
        }
    }

    // Output
    cout << "{\"placements\":[";
    bool first = true;
    for (auto& p : placements) {
        if (!first) cout << ",";
        first = false;
        cout << "{\"type\":\"" << p.type << "\",\"x\":" << p.x << ",\"y\":" << p.y << ",\"rot\":" << p.rot << "}";
    }
    cout << "]}" << endl;

    return 0;
}