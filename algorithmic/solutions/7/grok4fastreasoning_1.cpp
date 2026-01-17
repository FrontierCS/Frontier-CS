#include <bits/stdc++.h>
using namespace std;

void build_func(int cur, int rem, long long lo, long long hi, vector<vector<pair<int, int>>>& graph, const vector<int>& remain, int& node_cnt) {
    if (lo > hi || rem == 0) return;
    long long half = 1LL << (rem - 1);
    // 0 side
    long long lo0 = lo;
    long long hi0 = min(hi, half - 1);
    if (lo0 <= hi0) {
        bool full0 = (lo0 == 0 && hi0 == half - 1);
        int targ;
        if (full0) {
            targ = remain[rem - 1];
        } else {
            int nextn = ++node_cnt;
            targ = nextn;
            build_func(nextn, rem - 1, lo0, hi0, graph, remain, node_cnt);
        }
        graph[cur].emplace_back(targ, 0);
    }
    // 1 side
    long long lo1 = max(lo, half);
    long long hi1 = hi;
    if (lo1 <= hi1) {
        bool full1 = (lo1 == half && hi1 == ((1LL << rem) - 1));
        int targ;
        if (full1) {
            targ = remain[rem - 1];
        } else {
            int nextn = ++node_cnt;
            targ = nextn;
            build_func(nextn, rem - 1, lo1 - half, hi1 - half, graph, remain, node_cnt);
        }
        graph[cur].emplace_back(targ, 1);
    }
}

int main() {
    long long L, R;
    cin >> L >> R;
    int D = (R == 0 ? 0 : 64 - __builtin_clzll(R));
    int node_cnt = 2; // 1: start, 2: end
    vector<int> remain(D + 1, 0);
    remain[0] = 2;
    for (int r = 1; r <= D; ++r) {
        int newn = ++node_cnt;
        remain[r] = newn;
    }
    vector<vector<pair<int, int>>> graph(node_cnt + 1);
    for (int r = 1; r <= D; ++r) {
        int from = remain[r];
        int to = remain[r - 1];
        graph[from].emplace_back(to, 0);
        graph[from].emplace_back(to, 1);
    }
    for (int d = 1; d <= D; ++d) {
        long long fl = (d == 1 ? 1LL : (1LL << (d - 1)));
        long long fh = fl * 2 - 1;
        long long al = max(L, fl);
        long long ah = min(R, fh);
        if (al > ah) continue;
        bool is_full = (al == fl && ah == fh);
        int remm = d - 1;
        int targ = remain[remm];
        if (is_full) {
            graph[1].emplace_back(targ, 1);
        } else {
            if (d == 1) continue;
            int subs = ++node_cnt;
            graph[1].emplace_back(subs, 1);
            long long olo = al - fl;
            long long ohi = ah - fl;
            build_func(subs, remm, olo, ohi, graph, remain, node_cnt);
        }
    }
    // Now find reachable
    vector<bool> used(node_cnt + 1, false);
    queue<int> q;
    q.push(1);
    used[1] = true;
    while (!q.empty()) {
        int u = q.front();
        q.pop();
        for (auto& p : graph[u]) {
            int v = p.first;
            if (!used[v]) {
                used[v] = true;
                q.push(v);
            }
        }
    }
    vector<int> reachable;
    for (int i = 1; i <= node_cnt; ++i) {
        if (used[i]) reachable.push_back(i);
    }
    sort(reachable.begin(), reachable.end());
    int newn = reachable.size();
    map<int, int> remap;
    for (int j = 0; j < newn; ++j) {
        remap[reachable[j]] = j + 1;
    }
    vector<vector<pair<int, int>>> newgraph(newn + 1);
    for (int oldi : reachable) {
        int newi = remap[oldi];
        for (auto& p : graph[oldi]) {
            int olda = p.first;
            int newa = remap[olda];
            int vv = p.second;
            newgraph[newi].emplace_back(newa, vv);
        }
    }
    cout << newn << endl;
    for (int i = 1; i <= newn; ++i) {
        auto& e = newgraph[i];
        int k = e.size();
        cout << k;
        for (auto& p : e) {
            cout << " " << p.first << " " << p.second;
        }
        cout << endl;
    }
    return 0;
}