#include <bits/stdc++.h>
using namespace std;

struct Item {
    string name;
    long long q, v, m, l;
};

int main() {
    string s, line;
    while (getline(cin, line)) {
        s += line;
    }
    string compacted;
    for (char c : s) {
        if (!isspace(static_cast<unsigned char>(c))) {
            compacted += c;
        }
    }
    size_t pos = 0;
    if (compacted.empty() || compacted[pos] != '{') return 1;
    pos++;
    vector<pair<string, vector<long long>>> data;
    while (pos < compacted.size() && compacted[pos] != '}') {
        if (compacted[pos] != '"') return 1;
        pos++;
        string key;
        while (pos < compacted.size() && compacted[pos] != '"') {
            key += compacted[pos];
            pos++;
        }
        if (pos >= compacted.size() || compacted[pos] != '"') return 1;
        pos++;
        if (pos >= compacted.size() || compacted[pos] != ':') return 1;
        pos++;
        if (pos >= compacted.size() || compacted[pos] != '[') return 1;
        pos++;
        vector<long long> vals(4);
        for (int i = 0; i < 4; i++) {
            string numstr;
            while (pos < compacted.size() && isdigit(compacted[pos])) {
                numstr += compacted[pos];
                pos++;
            }
            if (numstr.empty()) return 1;
            vals[i] = stoll(numstr);
            if (i < 3) {
                if (pos >= compacted.size() || compacted[pos] != ',') return 1;
                pos++;
            }
        }
        if (pos >= compacted.size() || compacted[pos] != ']') return 1;
        pos++;
        data.push_back({key, vals});
        if (pos < compacted.size() && compacted[pos] == ',') pos++;
    }
    if (data.size() != 12) return 1;

    vector<Item> all_items(12);
    for (int i = 0; i < 12; i++) {
        all_items[i].name = data[i].first;
        all_items[i].q = data[i].second[0];
        all_items[i].v = data[i].second[1];
        all_items[i].m = data[i].second[2];
        all_items[i].l = data[i].second[3];
    }

    const long long MASS = 20000000LL;
    const long long VOL = 25000000LL;

    auto simulate = [&](const vector<int>& order) -> pair<long long, vector<long long>> {
        long long rem_m = MASS;
        long long rem_v = VOL;
        vector<long long> cnt(12, 0);
        long long tot = 0;
        for (int idx : order) {
            const auto& it = all_items[idx];
            long long xm = rem_m / it.m;
            long long xv = rem_v / it.l;
            long long x = min({it.q, xm, xv});
            if (x > 0) {
                cnt[idx] = x;
                tot += x * it.v;
                rem_m -= x * it.m;
                rem_v -= x * it.l;
            }
        }
        return {tot, cnt};
    };

    vector<pair<long long, vector<long long>>> candidates;

    // Heuristic 1: by v/m descending
    {
        vector<int> order(12);
        iota(order.begin(), order.end(), 0);
        sort(order.begin(), order.end(), [&](int i, int j) -> bool {
            long long a = all_items[i].v * all_items[j].m;
            long long b = all_items[j].v * all_items[i].m;
            return a > b;
        });
        candidates.push_back(simulate(order));
    }

    // Heuristic 2: by v/l descending
    {
        vector<int> order(12);
        iota(order.begin(), order.end(), 0);
        sort(order.begin(), order.end(), [&](int i, int j) -> bool {
            long long a = all_items[i].v * all_items[j].l;
            long long b = all_items[j].v * all_items[i].l;
            return a > b;
        });
        candidates.push_back(simulate(order));
    }

    // Heuristic 3: by v/(m+l) descending
    {
        vector<int> order(12);
        iota(order.begin(), order.end(), 0);
        sort(order.begin(), order.end(), [&](int i, int j) -> bool {
            long long ma = all_items[i].m + all_items[i].l;
            long long mb = all_items[j].m + all_items[j].l;
            long long a = all_items[i].v * mb;
            long long b = all_items[j].v * ma;
            return a > b;
        });
        candidates.push_back(simulate(order));
    }

    // Heuristic 4: by min(v/m, v/l) descending
    {
        vector<int> order(12);
        iota(order.begin(), order.end(), 0);
        sort(order.begin(), order.end(), [&](int i, int j) -> bool {
            double di = min((double)all_items[i].v / all_items[i].m, (double)all_items[i].v / all_items[i].l);
            double dj = min((double)all_items[j].v / all_items[j].m, (double)all_items[j].v / all_items[j].l);
            return di > dj;
        });
        candidates.push_back(simulate(order));
    }

    long long best = -1;
    vector<long long> best_cnt(12, 0);
    for (auto& p : candidates) {
        if (p.first > best) {
            best = p.first;
            best_cnt = p.second;
        }
    }

    cout << "{" << endl;
    for (int i = 0; i < 12; i++) {
        cout << " \"" << all_items[i].name << "\": " << best_cnt[i];
        if (i < 11) cout << ",";
        cout << endl;
    }
    cout << "}" << endl;

    return 0;
}