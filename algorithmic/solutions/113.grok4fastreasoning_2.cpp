#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;
    vector<uint64_t> power(n + 1, 0);
    power[1] = 1;
    for (int i = 2; i <= n; ++i) {
        power[i] = power[i - 1] * 3;
    }
    uint64_t initial = 0;
    uint64_t goal = 0;
    for (int i = 1; i <= n; ++i) {
        goal += 2ULL * power[i];
    }
    unordered_map<uint64_t, pair<uint64_t, pair<int, int>>> prev;
    queue<uint64_t> q;
    q.push(initial);
    prev[initial] = {0, {-1, -1}};
    bool found = false;
    while (!q.empty()) {
        uint64_t cur = q.front();
        q.pop();
        if (cur == goal) {
            found = true;
            break;
        }
        vector<int> pos(n + 1);
        uint64_t temp = cur;
        for (int i = 1; i <= n; ++i) {
            pos[i] = temp % 3;
            temp /= 3;
        }
        for (int f = 0; f < 3; ++f) {
            vector<int> fb;
            for (int i = 1; i <= n; ++i) {
                if (pos[i] == f) fb.push_back(i);
            }
            if (fb.empty()) continue;
            sort(fb.begin(), fb.end());
            int kk = fb.size();
            int ball = fb[kk / 2];
            for (int tt = 0; tt < 3; ++tt) {
                if (tt == f) continue;
                vector<int> tb;
                for (int i = 1; i <= n; ++i) {
                    if (pos[i] == tt) tb.push_back(i);
                }
                int cnt = 0;
                for (int b : tb) {
                    if (b < ball) ++cnt;
                }
                int tsize = tb.size();
                int req = (tsize + 1) / 2;
                if (cnt == req) {
                    vector<int> new_pos = pos;
                    new_pos[ball] = tt;
                    uint64_t newstate = 0;
                    for (int i = 1; i <= n; ++i) {
                        newstate += (uint64_t)new_pos[i] * power[i];
                    }
                    if (prev.find(newstate) == prev.end()) {
                        prev[newstate] = {cur, {f + 1, tt + 1}};
                        q.push(newstate);
                    }
                }
            }
        }
    }
    vector<pair<int, int>> path;
    uint64_t current = goal;
    while (current != initial) {
        auto p = prev[current];
        path.push_back(p.second);
        current = p.first;
    }
    reverse(path.begin(), path.end());
    cout << path.size() << endl;
    for (auto& m : path) {
        cout << m.first << " " << m.second << endl;
    }
    return 0;
}