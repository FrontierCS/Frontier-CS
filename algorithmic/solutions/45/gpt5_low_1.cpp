#include <bits/stdc++.h>
using namespace std;

struct FastIO {
    static const int S = 1 << 20;
    int wpos; char wbuf[S];
    FastIO() : wpos(0) {}
    inline int gc() {
        static char buf[S];
        static int len = 0, pos = 0;
        if (pos == len) pos = 0, len = (int)fread(buf, 1, S, stdin);
        if (pos == len) return -1;
        return buf[pos++];
    }
    template <class T>
    bool readInt(T &out) {
        int c, s = 1; T x = 0;
        c = gc();
        if (c == -1) return false;
        while (c <= ' ') { c = gc(); if (c == -1) return false; }
        if (c == '-') s = -1, c = gc();
        for (; c >= '0' && c <= '9'; c = gc()) x = x * 10 + (c - '0');
        out = x * s;
        return true;
    }
    bool readDouble(double &out) {
        int c = gc();
        if (c == -1) return false;
        while (c <= ' ') { c = gc(); if (c == -1) return false; }
        int sgn = 1;
        if (c == '-') { sgn = -1; c = gc(); }
        long long intPart = 0;
        while (c >= '0' && c <= '9') { intPart = intPart * 10 + (c - '0'); c = gc(); }
        double frac = 0.0, base = 1.0;
        if (c == '.') {
            c = gc();
            while (c >= '0' && c <= '9') {
                frac = frac * 10 + (c - '0');
                base *= 10.0;
                c = gc();
            }
        }
        out = sgn * (intPart + frac / base);
        return true;
    }
    ~FastIO() { flush(); }
    inline void pc(char c) { if (wpos == S) flush(); wbuf[wpos++] = c; }
    inline void flush() { if (wpos) { fwrite(wbuf, 1, wpos, stdout); wpos = 0; } }
    template <class T>
    inline void writeInt(T x, char end) {
        if (x == 0) { pc('0'); if (end) pc(end); return; }
        if (x < 0) pc('-'), x = -x;
        char s[24]; int n = 0;
        while (x) s[n++] = char('0' + (x % 10)), x /= 10;
        while (n--) pc(s[n]);
        if (end) pc(end);
    }
} io;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastIO fio;
    int n, m, k;
    double eps;
    if (!fio.readInt(n)) return 0;
    fio.readInt(m);
    fio.readInt(k);
    fio.readDouble(eps);

    vector<pair<int,int>> edges;
    edges.reserve(m);
    for (int i = 0; i < m; ++i) {
        int u, v;
        if (!fio.readInt(u)) u = 0;
        fio.readInt(v);
        if (u == v) continue;
        if (u > v) swap(u, v);
        edges.emplace_back(u, v);
    }

    sort(edges.begin(), edges.end());
    edges.erase(unique(edges.begin(), edges.end()), edges.end());
    int M = (int)edges.size();

    vector<int> deg(n + 1, 0);
    for (auto &e : edges) {
        deg[e.first]++;
        deg[e.second]++;
    }

    vector<int> off(n + 2, 0);
    for (int i = 1; i <= n; ++i) off[i+1] = off[i] + deg[i];
    vector<int> adj(2 * M);
    vector<int> cur = off;
    for (auto &e : edges) {
        int u = e.first, v = e.second;
        adj[cur[u]++] = v;
        adj[cur[v]++] = u;
    }

    // Compute capacities
    int ideal = (n + k - 1) / k;
    long double cap_d = floor((1.0L + (long double)eps) * (long double)ideal);
    int cap = (int)cap_d;
    if (cap < 0) cap = ideal; // safety

    vector<int> part(n + 1, -1);
    vector<int> psz(k, 0);

    // Seed with top-degree vertices for first min(k, n) parts
    vector<int> vid(n);
    for (int i = 0; i < n; ++i) vid[i] = i + 1;
    sort(vid.begin(), vid.end(), [&](int a, int b){ return (deg[a] > deg[b]) || (deg[a] == deg[b] && a < b); });
    int seeds = min(k, n);
    for (int i = 0; i < seeds; ++i) {
        int v = vid[i];
        if (part[v] == -1 && psz[i] < cap) {
            part[v] = i;
            psz[i]++;
        }
    }

    // Order for streaming assignment
    std::mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    vector<int> order(n);
    for (int i = 0; i < n; ++i) order[i] = i + 1;
    shuffle(order.begin(), order.end(), rng);

    vector<int> cnt(k, 0), vis(k, -1);
    int iter = 0;

    // Initial greedy assignment (LDG-like)
    for (int idx = 0; idx < n; ++idx) {
        int v = order[idx];
        if (part[v] != -1) continue;
        iter++;
        int start = off[v], end = off[v+1];
        for (int ei = start; ei < end; ++ei) {
            int u = adj[ei];
            int pu = part[u];
            if (pu >= 0) {
                if (vis[pu] != iter) { vis[pu] = iter; cnt[pu] = 0; }
                cnt[pu]++;
            }
        }
        int best = -1;
        int bestScore = -1;
        // A slight size penalty to encourage balance
        for (int j = 0; j < k; ++j) {
            if (psz[j] >= cap) continue;
            int c = (vis[j] == iter) ? cnt[j] : 0;
            // tie-break by smaller size, then by random
            if (c > bestScore) {
                bestScore = c; best = j;
            } else if (c == bestScore && best != -1) {
                if (psz[j] < psz[best]) best = j;
            } else if (best == -1) {
                best = j;
            }
        }
        if (best == -1) {
            // Fallback: choose minimal size part (should be rare/impossible)
            int jbest = 0;
            for (int j = 1; j < k; ++j) if (psz[j] < psz[jbest]) jbest = j;
            best = jbest;
        }
        part[v] = best;
        psz[best]++;
    }

    // Refinement: 2 passes of balanced label propagation
    int passes = 2;
    for (int pass = 0; pass < passes; ++pass) {
        shuffle(order.begin(), order.end(), rng);
        bool moved_any = false;
        for (int idx = 0; idx < n; ++idx) {
            int v = order[idx];
            int a = part[v];
            iter++;
            int start = off[v], end = off[v+1];
            for (int ei = start; ei < end; ++ei) {
                int u = adj[ei];
                int pu = part[u];
                if (vis[pu] != iter) { vis[pu] = iter; cnt[pu] = 0; }
                cnt[pu]++;
            }
            int best = a;
            int bestScore = (vis[a] == iter) ? cnt[a] : 0;
            for (int j = 0; j < k; ++j) {
                if (j == a) continue;
                if (psz[j] >= cap) continue;
                int c = (vis[j] == iter) ? cnt[j] : 0;
                if (c > bestScore) {
                    bestScore = c; best = j;
                } else if (c == bestScore && c > 0) {
                    if (psz[j] + 1 <= psz[best] - (best == a ? 1 : 0)) best = j;
                }
            }
            if (best != a && bestScore > ((vis[a] == iter) ? cnt[a] : 0)) {
                part[v] = best;
                psz[best]++; psz[a]--;
                moved_any = true;
            } else if (best != a && bestScore == ((vis[a] == iter) ? cnt[a] : 0)) {
                // tie: improve balance
                if (psz[best] + 1 <= psz[a] - 1) {
                    part[v] = best;
                    psz[best]++; psz[a]--;
                    moved_any = true;
                }
            }
        }
        if (!moved_any) break;
    }

    // Output 1-based part labels
    for (int i = 1; i <= n; ++i) {
        fio.writeInt(part[i] + 1, i == n ? '\n' : ' ');
    }
    return 0;
}