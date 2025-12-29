#include <bits/stdc++.h>
using namespace std;

struct Item {
    string type_id;
    int w, h, v, limit;
    double density() const {
        return 1.0 * v / (w * h);
    }
};

vector<tuple<string, int, int, int>> get_placements(const vector<int>& order, int W, int H, bool allow_rotate, const vector<Item>& items) {
    vector<int> sky(W, 0);
    vector<tuple<string, int, int, int>> placements;
    int M = items.size();
    vector<int> used(M, 0);
    struct Candidate {
        int y, x, rot, ww, hh;
        bool operator<(const Candidate& o) const {
            if (y != o.y) return y < o.y;
            return x < o.x;
        }
    };
    for (int idx : order) {
        const Item& it = items[idx];
        int max_count = it.limit - used[idx];
        bool can_place_more = true;
        for (int cnt = 0; cnt < max_count && can_place_more; ++cnt) {
            vector<Candidate> cands;
            // rot 0
            {
                int ww = it.w;
                int hh = it.h;
                if (ww <= W && hh <= H) {
                    vector<int> wmax(W - ww + 1, 0);
                    deque<int> dq;
                    for (int i = 0; i < W; ++i) {
                        if (!dq.empty() && dq.front() == i - ww) dq.pop_front();
                        while (!dq.empty() && sky[dq.back()] <= sky[i]) dq.pop_back();
                        dq.push_back(i);
                        if (i >= ww - 1) {
                            int sx = i - ww + 1;
                            wmax[sx] = sky[dq.front()];
                        }
                    }
                    int best_y = INT_MAX;
                    int best_x = INT_MAX;
                    for (int sx = 0; sx <= W - ww; ++sx) {
                        int yv = wmax[sx];
                        if (yv + hh <= H) {
                            if (yv < best_y || (yv == best_y && sx < best_x)) {
                                best_y = yv;
                                best_x = sx;
                            }
                        }
                    }
                    if (best_y != INT_MAX) {
                        cands.push_back({best_y, best_x, 0, ww, hh});
                    }
                }
            }
            // rot 1
            if (allow_rotate) {
                int ww = it.h;
                int hh = it.w;
                if (ww <= W && hh <= H) {
                    vector<int> wmax(W - ww + 1, 0);
                    deque<int> dq;
                    for (int i = 0; i < W; ++i) {
                        if (!dq.empty() && dq.front() == i - ww) dq.pop_front();
                        while (!dq.empty() && sky[dq.back()] <= sky[i]) dq.pop_back();
                        dq.push_back(i);
                        if (i >= ww - 1) {
                            int sx = i - ww + 1;
                            wmax[sx] = sky[dq.front()];
                        }
                    }
                    int best_y = INT_MAX;
                    int best_x = INT_MAX;
                    for (int sx = 0; sx <= W - ww; ++sx) {
                        int yv = wmax[sx];
                        if (yv + hh <= H) {
                            if (yv < best_y || (yv == best_y && sx < best_x)) {
                                best_y = yv;
                                best_x = sx;
                            }
                        }
                    }
                    if (best_y != INT_MAX) {
                        cands.push_back({best_y, best_x, 1, ww, hh});
                    }
                }
            }
            if (cands.empty()) {
                can_place_more = false;
                continue;
            }
            sort(cands.begin(), cands.end());
            auto& best = cands[0];
            int px = best.x;
            int py = best.y;
            int prot = best.rot;
            string ptype = it.type_id;
            placements.emplace_back(ptype, px, py, prot);
            used[idx]++;
            for (int j = px; j < px + best.ww; ++j) {
                sky[j] = max(sky[j], py + best.hh);
            }
        }
    }
    return placements;
}

int main() {
    string input((istreambuf_iterator<char>(cin)), istreambuf_iterator<char>());
    string clean;
    for (char c : input) if (!isspace(c)) clean += c;

    // parse bin
    size_t pos = clean.find("\"W\":") + 4;
    int W = 0;
    while (isdigit(clean[pos])) {
        W = W * 10 + clean[pos] - '0';
        ++pos;
    }
    pos = clean.find("\"H\":") + 4;
    int H = 0;
    while (isdigit(clean[pos])) {
        H = H * 10 + clean[pos] - '0';
        ++pos;
    }
    pos = clean.find("\"allow_rotate\":") + 15;
    bool allow_rotate = (clean[pos] == 't');

    // parse items
    vector<Item> items;
    size_t items_start = clean.find("\"items\":[") + 9;
    size_t current = items_start;
    while (current < clean.size()) {
        size_t type_pos = clean.find("\"type\":\"", current);
        if (type_pos == string::npos) break;
        type_pos += 8;
        string type_id;
        current = type_pos;
        while (clean[current] != '"') {
            type_id += clean[current];
            ++current;
        }
        ++current;  // skip "
        size_t w_pos = clean.find("\"w\":", current) + 4;
        int iw = 0;
        current = w_pos;
        while (isdigit(clean[current])) {
            iw = iw * 10 + clean[current] - '0';
            ++current;
        }
        size_t h_pos = clean.find("\"h\":", current) + 4;
        int ih = 0;
        current = h_pos;
        while (isdigit(clean[current])) {
            ih = ih * 10 + clean[current] - '0';
            ++current;
        }
        size_t v_pos = clean.find("\"v\":", current) + 4;
        int iv = 0;
        current = v_pos;
        while (isdigit(clean[current])) {
            iv = iv * 10 + clean[current] - '0';
            ++current;
        }
        size_t l_pos = clean.find("\"limit\":", current) + 8;
        int il = 0;
        current = l_pos;
        while (isdigit(clean[current])) {
            il = il * 10 + clean[current] - '0';
            ++current;
        }
        size_t obj_end = clean.find("}", current);
        current = obj_end + 1;
        if (current < clean.size() && clean[current] == ',') ++current;
        items.push_back({type_id, iw, ih, iv, il});
    }
    int M = items.size();

    map<string, int> type_to_v;
    for (const auto& it : items) {
        type_to_v[it.type_id] = it.v;
    }

    vector<vector<int>> strategies;
    vector<int> ord(M);
    iota(ord.begin(), ord.end(), 0);

    // density desc
    sort(ord.begin(), ord.end(), [&](int a, int b) {
        double da = items[a].density(), db = items[b].density();
        if (da != db) return da > db;
        return a < b;
    });
    strategies.push_back(ord);

    // height desc
    iota(ord.begin(), ord.end(), 0);
    sort(ord.begin(), ord.end(), [&](int a, int b) {
        if (items[a].h != items[b].h) return items[a].h > items[b].h;
        return a < b;
    });
    strategies.push_back(ord);

    // width desc
    iota(ord.begin(), ord.end(), 0);
    sort(ord.begin(), ord.end(), [&](int a, int b) {
        if (items[a].w != items[b].w) return items[a].w > items[b].w;
        return a < b;
    });
    strategies.push_back(ord);

    // profit desc
    iota(ord.begin(), ord.end(), 0);
    sort(ord.begin(), ord.end(), [&](int a, int b) {
        if (items[a].v != items[b].v) return items[a].v > items[b].v;
        return a < b;
    });
    strategies.push_back(ord);

    // input order
    iota(ord.begin(), ord.end(), 0);
    strategies.push_back(ord);

    long long best_profit = -1;
    vector<tuple<string, int, int, int>> best_placements;
    for (const auto& order : strategies) {
        auto pls = get_placements(order, W, H, allow_rotate, items);
        long long profit = 0;
        for (const auto& [tp, x, y, r] : pls) {
            profit += type_to_v[tp];
        }
        if (profit > best_profit) {
            best_profit = profit;
            best_placements = std::move(pls);
        }
    }

    // output
    cout << "{\n  \"placements\": [\n";
    for (size_t i = 0; i < best_placements.size(); ++i) {
        auto [tp, x, y, r] = best_placements[i];
        cout << "    {\"type\":\"" << tp << "\",\"x\":" << x << ",\"y\":" << y << ",\"rot\":" << r << "}";
        if (i + 1 < best_placements.size()) cout << ",";
        cout << "\n";
    }
    cout << "  ]\n}\n";
    return 0;
}