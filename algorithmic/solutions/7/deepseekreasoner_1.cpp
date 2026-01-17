#include <bits/stdc++.h>
using namespace std;

struct State {
    int i, low, high;
    bool operator<(const State& other) const {
        if (i != other.i) return i < other.i;
        if (low != other.low) return low < other.low;
        return high < other.high;
    }
};

int main() {
    int L, R;
    cin >> L >> R;

    auto get_bin = [](int x) -> vector<int> {
        vector<int> res;
        while (x > 0) {
            res.push_back(x % 2);
            x /= 2;
        }
        reverse(res.begin(), res.end());
        return res;
    };

    vector<int> L_bin = get_bin(L);
    vector<int> R_bin = get_bin(R);
    int lenL = L_bin.size();
    int lenR = R_bin.size();

    vector<vector<vector<bool>>> productive(lenR, vector<vector<bool>>(2, vector<bool>(2, false)));

    for (int i = lenR - 1; i >= 0; --i) {
        for (int low = 0; low <= 1; ++low) {
            for (int high = 0; high <= 1; ++high) {
                for (int b = 0; b <= 1; ++b) {
                    bool ok = true;
                    if (low == 1 && i < lenL && b < L_bin[i]) ok = false;
                    if (high == 1 && i < lenR && b > R_bin[i]) ok = false;
                    if (!ok) continue;

                    if (i + 1 >= lenL && i + 1 <= lenR) productive[i][low][high] = true;
                    if (i + 1 < lenR) {
                        int new_low = (low && i < lenL && b == L_bin[i]) ? 1 : 0;
                        int new_high = (high && i < lenR && b == R_bin[i]) ? 1 : 0;
                        if (productive[i + 1][new_low][new_high])
                            productive[i][low][high] = true;
                    }
                }
            }
        }
    }

    map<State, int> idMap;
    vector<vector<pair<int, int>>> edges(1);
    int next_id = 1;
    State start{0, 1, 1};
    idMap[start] = next_id++;
    edges.push_back({});
    queue<State> q;
    q.push(start);

    while (!q.empty()) {
        State s = q.front(); q.pop();
        int u = idMap[s];
        for (int b = 0; b <= 1; ++b) {
            if (s.low == 1 && s.i < lenL && b < L_bin[s.i]) continue;
            if (s.high == 1 && s.i < lenR && b > R_bin[s.i]) continue;

            if (s.i + 1 >= lenL && s.i + 1 <= lenR)
                edges[u].push_back({0, b});

            if (s.i + 1 < lenR) {
                int new_low = (s.low && s.i < lenL && b == L_bin[s.i]) ? 1 : 0;
                int new_high = (s.high && s.i < lenR && b == R_bin[s.i]) ? 1 : 0;
                if (productive[s.i + 1][new_low][new_high]) {
                    State ns{s.i + 1, new_low, new_high};
                    if (!idMap.count(ns)) {
                        idMap[ns] = next_id++;
                        edges.push_back({});
                        q.push(ns);
                    }
                    int v = idMap[ns];
                    edges[u].push_back({v, b});
                }
            }
        }
    }

    int state_count = idMap.size();
    int T_id = state_count + 1;
    int n = T_id;

    cout << n << "\n";
    for (int u = 1; u <= state_count; ++u) {
        cout << edges[u].size();
        for (auto& e : edges[u]) {
            int to = e.first, w = e.second;
            if (to == 0) to = T_id;
            cout << " " << to << " " << w;
        }
        cout << "\n";
    }
    cout << "0\n";

    return 0;
}