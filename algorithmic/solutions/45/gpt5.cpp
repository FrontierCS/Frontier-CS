#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static const int BUFSIZE = 1 << 20;
    int idx, size;
    char buf[BUFSIZE];
    FastScanner(): idx(0), size(0) {}
    inline char getch() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }
    template<typename T>
    bool readInt(T &out) {
        char c = getch();
        if (!c) return false;
        while (c!='-' && (c<'0' || c>'9')) { c = getch(); if (!c) return false; }
        int sign = 1;
        if (c == '-') { sign = -1; c = getch(); }
        long long x = 0;
        while (c >= '0' && c <= '9') {
            x = x * 10 + (c - '0');
            c = getch();
        }
        out = (T)(x * sign);
        return true;
    }
    bool readDouble(double &out) {
        char c = getch();
        if (!c) return false;
        while (c!='-' && c!='.' && (c<'0'||c>'9')) { c = getch(); if (!c) return false; }
        int sign = 1;
        if (c == '-') { sign = -1; c = getch(); }
        long long intPart = 0;
        while (c >= '0' && c <= '9') { intPart = intPart*10 + (c - '0'); c = getch(); }
        double val = (double)intPart;
        if (c == '.') {
            double factor = 1.0;
            c = getch();
            while (c >= '0' && c <= '9') {
                factor *= 0.1;
                val += (c - '0') * factor;
                c = getch();
            }
        }
        out = sign * val;
        return true;
    }
} In;

struct FastOutput {
    static const int BUFSIZE = 1 << 20;
    int idx;
    char buf[BUFSIZE];
    FastOutput(): idx(0) {}
    ~FastOutput() { flush(); }
    inline void pushChar(char c) {
        if (idx >= BUFSIZE) flush();
        buf[idx++] = c;
    }
    inline void flush() {
        if (idx) {
            fwrite(buf, 1, idx, stdout);
            idx = 0;
        }
    }
    inline void writeInt(int x) {
        if (x < 0) { pushChar('-'); x = -x; }
        char s[16]; int n = 0;
        do { s[n++] = char('0' + (x % 10)); x /= 10; } while (x);
        while (n--) pushChar(s[n]);
    }
} Out;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m, k;
    double eps;
    if (!In.readInt(n)) return 0;
    In.readInt(m);
    In.readInt(k);
    In.readDouble(eps);

    vector<uint64_t> edges;
    edges.reserve((size_t)m);
    for (int i = 0; i < m; ++i) {
        int u, v;
        if (!In.readInt(u)) u = 0;
        In.readInt(v);
        if (u == v) continue;
        if (u > v) swap(u, v);
        uint64_t key = ( (uint64_t)(uint32_t)u << 32 ) | (uint32_t)v;
        edges.push_back(key);
    }

    sort(edges.begin(), edges.end());
    edges.erase(unique(edges.begin(), edges.end()), edges.end());
    size_t E = edges.size();

    vector<int> deg(n + 1, 0);
    for (size_t i = 0; i < E; ++i) {
        int u = (int)(edges[i] >> 32);
        int v = (int)(edges[i] & 0xffffffffu);
        deg[u]++; deg[v]++;
    }

    vector<int> head(n + 2, 0);
    for (int i = 1; i <= n; ++i) head[i + 1] = head[i] + deg[i];
    vector<int> adj(2 * E);
    vector<int> cur = head;
    for (size_t i = 0; i < E; ++i) {
        int u = (int)(edges[i] >> 32);
        int v = (int)(edges[i] & 0xffffffffu);
        adj[cur[u]++] = v;
        adj[cur[v]++] = u;
    }
    edges.clear(); edges.shrink_to_fit();

    long long ideal = (n + k - 1) / k;
    long long cap_ll = (long long)floor((1.0 + eps) * (double)ideal);
    int cap = (int)cap_ll;

    vector<int> part(n + 1, 0);
    vector<int> psize(k + 1, 0);

    // Pick k seeds with largest degrees
    priority_queue<pair<int,int>, vector<pair<int,int>>, greater<pair<int,int>>> pq;
    for (int i = 1; i <= n; ++i) {
        if ((int)pq.size() < k) pq.emplace(deg[i], i);
        else if (deg[i] > pq.top().first) { pq.pop(); pq.emplace(deg[i], i); }
    }
    vector<int> seeds;
    seeds.reserve(k);
    while (!pq.empty()) { seeds.push_back(pq.top().second); pq.pop(); }
    while ((int)seeds.size() < k) {
        // In rare case n<k or degs duplicates, fill remaining with any unused vertices
        seeds.push_back((int)seeds.size() + 1);
        if ((int)seeds.back() > n) seeds.back() = 1;
    }
    // ensure uniqueness of seeds
    vector<char> usedSeed(n + 1, 0);
    for (int i = 0, j = 1; i < k; ++i) {
        int s = seeds[i];
        if (s < 1 || s > n || usedSeed[s]) {
            while (j <= n && usedSeed[j]) ++j;
            if (j <= n) s = j++;
            else s = 1;
        }
        usedSeed[s] = 1;
        seeds[i] = s;
    }

    vector<vector<int>> queues(k + 1);
    vector<int> qhead(k + 1, 0);

    int remaining = n;
    for (int i = 1; i <= k; ++i) {
        int s = seeds[i - 1];
        if (part[s] == 0) {
            part[s] = i;
            psize[i]++;
            queues[i].push_back(s);
            remaining--;
        }
    }

    // Round-robin BFS expansion while possible
    bool progress = true;
    while (remaining > 0) {
        progress = false;
        for (int i = 1; i <= k; ++i) {
            if (psize[i] >= cap) continue;
            while (psize[i] < cap && qhead[i] < (int)queues[i].size()) {
                int v = queues[i][qhead[i]++];
                int l = head[v], r = head[v + 1];
                for (int it = l; it < r; ++it) {
                    int u = adj[it];
                    if (part[u] == 0) {
                        part[u] = i;
                        psize[i]++;
                        queues[i].push_back(u);
                        remaining--;
                        progress = true;
                        if (psize[i] >= cap) break;
                    }
                }
                if (psize[i] >= cap) break;
            }
        }
        if (!progress) break;
    }

    // If some vertices remain unassigned (due to disconnected components or capacity stops), seed new BFS in least filled parts
    int nextUnassigned = 1;
    auto findLeastFilledPart = [&]() -> int {
        int best = -1, bestSz = INT_MAX;
        for (int i = 1; i <= k; ++i) {
            if (psize[i] < cap) {
                if (psize[i] < bestSz) { bestSz = psize[i]; best = i; }
            }
        }
        return best;
    };
    while (remaining > 0) {
        int pi = findLeastFilledPart();
        if (pi == -1) break; // Shouldn't happen
        while (nextUnassigned <= n && part[nextUnassigned] != 0) ++nextUnassigned;
        if (nextUnassigned > n) break; // Shouldn't happen
        int s = nextUnassigned;
        part[s] = pi;
        psize[pi]++;
        queues[pi].push_back(s);
        remaining--;
        while (psize[pi] < cap && qhead[pi] < (int)queues[pi].size()) {
            int v = queues[pi][qhead[pi]++];
            int l = head[v], r = head[v + 1];
            for (int it = l; it < r; ++it) {
                int u = adj[it];
                if (part[u] == 0) {
                    part[u] = pi;
                    psize[pi]++;
                    queues[pi].push_back(u);
                    remaining--;
                    if (psize[pi] >= cap) break;
                }
            }
            if (psize[pi] >= cap) break;
        }
    }

    // Local refinement: one forward and one backward pass
    vector<int> cnt(k + 1, 0);
    vector<int> touched; touched.reserve(64);
    for (int pass = 0; pass < 2; ++pass) {
        if (pass == 0) {
            for (int v = 1; v <= n; ++v) {
                int curPart = part[v];
                int l = head[v], r = head[v + 1];
                touched.clear();
                // Count neighbor parts
                for (int it = l; it < r; ++it) {
                    int u = adj[it];
                    int p = part[u];
                    if (p == 0) continue;
                    if (cnt[p] == 0) touched.push_back(p);
                    cnt[p]++;
                }
                int eP = cnt[curPart];
                int bestPart = curPart;
                int bestGain = 0;
                for (int p : touched) {
                    if (p == curPart) continue;
                    if (psize[p] + 1 > cap) continue;
                    int gain = cnt[p] - eP;
                    if (gain > bestGain) {
                        bestGain = gain;
                        bestPart = p;
                    } else if (gain == bestGain && gain > 0) {
                        // tie-break by smaller target size
                        if (psize[p] < psize[bestPart]) bestPart = p;
                    }
                }
                // Clear counts
                for (int p : touched) cnt[p] = 0;
                if (bestPart != curPart) {
                    part[v] = bestPart;
                    psize[curPart]--;
                    psize[bestPart]++;
                }
            }
        } else {
            for (int v = n; v >= 1; --v) {
                int curPart = part[v];
                int l = head[v], r = head[v + 1];
                touched.clear();
                for (int it = l; it < r; ++it) {
                    int u = adj[it];
                    int p = part[u];
                    if (p == 0) continue;
                    if (cnt[p] == 0) touched.push_back(p);
                    cnt[p]++;
                }
                int eP = cnt[curPart];
                int bestPart = curPart;
                int bestGain = 0;
                for (int p : touched) {
                    if (p == curPart) continue;
                    if (psize[p] + 1 > cap) continue;
                    int gain = cnt[p] - eP;
                    if (gain > bestGain) {
                        bestGain = gain;
                        bestPart = p;
                    } else if (gain == bestGain && gain > 0) {
                        if (psize[p] < psize[bestPart]) bestPart = p;
                    }
                }
                for (int p : touched) cnt[p] = 0;
                if (bestPart != curPart) {
                    part[v] = bestPart;
                    psize[curPart]--;
                    psize[bestPart]++;
                }
            }
        }
    }

    // Output
    for (int i = 1; i <= n; ++i) {
        Out.writeInt(part[i] >= 1 ? part[i] : 1);
        if (i < n) Out.pushChar(' ');
    }
    Out.pushChar('\n');
    Out.flush();
    return 0;
}