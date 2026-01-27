#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    int a_dummy;
    for (int i = 0; i < 10; ++i) cin >> a_dummy;
    
    vector<vector<int>> out(n + 1), in(n + 1);
    out.reserve(n + 1);
    in.reserve(n + 1);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        out[u].push_back(v);
        in[v].push_back(u);
    }
    
    // Randomize start order
    vector<int> order(n);
    iota(order.begin(), order.end(), 1);
    mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());
    shuffle(order.begin(), order.end(), rng);
    
    // Arrays
    vector<int> nxt(n + 1, -1), prv(n + 1, -1);
    vector<char> vis(n + 1, 0);
    vector<int> posOut(n + 1, 0), posIn(n + 1, 0);
    vector<int> comp(n + 1, -1);
    vector<int> head_map(n + 1, -1), tail_map(n + 1, -1);
    
    // Path structures
    vector<int> headOf, tailOf, sizeOfPath, parent;
    vector<char> active;
    headOf.reserve(n);
    tailOf.reserve(n);
    sizeOfPath.reserve(n);
    parent.reserve(n);
    active.reserve(n);
    
    auto findp = [&](int x) {
        int r = x;
        while (parent[r] != r) r = parent[r];
        while (parent[x] != x) {
            int p = parent[x];
            parent[x] = r;
            x = p;
        }
        return r;
    };
    
    // Build initial maximal paths
    int path_count = 0;
    for (int s : order) {
        if (vis[s]) continue;
        deque<int> dq;
        dq.push_back(s);
        vis[s] = 1;
        int head = s, tail = s;
        while (true) {
            bool extended = false;
            // extend tail as far as possible
            while (true) {
                int u = tail;
                int &p = posOut[u];
                while (p < (int)out[u].size() && vis[out[u][p]]) ++p;
                if (p >= (int)out[u].size()) break;
                int w = out[u][p++];
                dq.push_back(w);
                vis[w] = 1;
                tail = w;
                extended = true;
            }
            // extend head as far as possible
            while (true) {
                int u = head;
                int &p = posIn[u];
                while (p < (int)in[u].size() && vis[in[u][p]]) ++p;
                if (p >= (int)in[u].size()) break;
                int w = in[u][p++];
                dq.push_front(w);
                vis[w] = 1;
                head = w;
                extended = true;
            }
            if (!extended) break;
        }
        // link dq into next/prev
        if (!dq.empty()) {
            for (size_t i = 0; i + 1 < dq.size(); ++i) {
                int u = dq[i], v = dq[i + 1];
                nxt[u] = v;
                prv[v] = u;
            }
            int pid = path_count++;
            headOf.push_back(head);
            tailOf.push_back(tail);
            sizeOfPath.push_back((int)dq.size());
            parent.push_back(pid);
            active.push_back(1);
            head_map[head] = pid;
            tail_map[tail] = pid;
            for (int x : dq) comp[x] = pid;
        }
    }
    
    // DSU find with lambda needs capturing parent by reference; define a function instead
    function<int(int)> Find = [&](int x)->int {
        if (parent[x] == x) return x;
        parent[x] = Find(parent[x]);
        return parent[x];
    };
    
    // Merge paths greedily by tail->head edges
    queue<int> q;
    for (int i = 0; i < path_count; ++i) q.push(i);
    
    while (!q.empty()) {
        int pid = q.front(); q.pop();
        int rep = Find(pid);
        if (!active[rep]) continue;
        int u = tailOf[rep];
        if (u == -1) continue;
        bool merged = false;
        for (int v : out[u]) {
            int pid2 = head_map[v];
            if (pid2 == -1) continue;
            int rep2 = Find(pid2);
            rep = Find(rep);
            if (!active[rep] || !active[rep2]) continue;
            if (rep2 == rep) continue;
            // link rep tail u to rep2 head v
            // sanity: u should be tail (nxt[u] == -1), v should be head (prv[v] == -1)
            // but not strictly enforced; proceed
            nxt[u] = v;
            prv[v] = u;
            // union by size, but preserve path orientation rep -> rep2
            int big = (sizeOfPath[rep] >= sizeOfPath[rep2]) ? rep : rep2;
            int small = (big == rep ? rep2 : rep);
            parent[small] = big;
            int newHead = headOf[rep];
            int newTail = tailOf[rep2];
            headOf[big] = newHead;
            tailOf[big] = newTail;
            sizeOfPath[big] = sizeOfPath[rep] + sizeOfPath[rep2];
            active[small] = 0;
            // update maps
            head_map[v] = -1; // v is no longer a head
            head_map[newHead] = big;
            tail_map[u] = -1; // u is no longer a tail
            tail_map[newTail] = big;
            // relabel comp for vertices in 'small'
            int cur = headOf[small];
            while (cur != -1) {
                comp[cur] = big;
                if (cur == tailOf[small]) break;
                cur = nxt[cur];
            }
            q.push(big);
            merged = true;
            break; // u is no longer tail, stop scanning its edges
        }
        (void)merged;
    }
    
    // Choose largest path
    int bestRep = -1, bestSize = -1;
    for (int i = 0; i < path_count; ++i) {
        int rep = Find(i);
        if (!active[rep]) continue;
        if (sizeOfPath[rep] > bestSize) {
            bestSize = sizeOfPath[rep];
            bestRep = rep;
        }
    }
    if (bestRep == -1) {
        // Fallback: output single vertex
        cout << 1 << "\n1\n";
        return 0;
    }
    
    // Output the path
    vector<int> ans;
    ans.reserve(sizeOfPath[bestRep]);
    int cur = headOf[bestRep];
    while (cur != -1) {
        ans.push_back(cur);
        if (cur == tailOf[bestRep]) break;
        cur = nxt[cur];
    }
    
    cout << (int)ans.size() << "\n";
    for (size_t i = 0; i < ans.size(); ++i) {
        if (i) cout << ' ';
        cout << ans[i];
    }
    cout << "\n";
    return 0;
}