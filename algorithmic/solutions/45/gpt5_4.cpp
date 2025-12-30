#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static inline int gc() {
    #ifdef _WIN32
        return getchar();
    #else
        return getchar_unlocked();
    #endif
    }
    bool skipBlanks() {
        int c;
        do {
            c = gc();
            if (c == EOF) return false;
        } while (c <= ' ');
        ungetc(c, stdin);
        return true;
    }
    bool nextInt(int &out) {
        if (!skipBlanks()) return false;
        int c = gc();
        int sign = 1;
        if (c == '-') { sign = -1; c = gc(); }
        int x = 0;
        for (; c > ' '; c = gc()) x = x * 10 + (c - '0');
        out = x * sign;
        return true;
    }
    bool nextLongLong(long long &out) {
        if (!skipBlanks()) return false;
        int c = gc();
        long long sign = 1;
        if (c == '-') { sign = -1; c = gc(); }
        long long x = 0;
        for (; c > ' '; c = gc()) x = x * 10 + (c - '0');
        out = x * sign;
        return true;
    }
    bool nextToken(string &s) {
        if (!skipBlanks()) return false;
        s.clear();
        int c = gc();
        for (; c > ' '; c = gc()) s.push_back((char)c);
        return true;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Use FastScanner for speed
    FastScanner fs;
    int n, k;
    long long m;
    string epsToken;
    if (!fs.nextInt(n)) return 0;
    if (!fs.nextLongLong(m)) return 0;
    if (!fs.nextInt(k)) return 0;
    if (!fs.nextToken(epsToken)) return 0;
    double eps = 0.0;
    try { eps = stod(epsToken); } catch (...) { eps = 0.0; }

    // Read edges and build degree counts, skipping self-loops
    vector<int> deg(n + 1, 0);
    vector<int> Eu;
    vector<int> Ev;
    Eu.reserve((size_t)m);
    Ev.reserve((size_t)m);
    for (long long i = 0; i < m; ++i) {
        int u, v;
        if (!fs.nextInt(u)) u = 0;
        if (!fs.nextInt(v)) v = 0;
        if (u < 1 || u > n || v < 1 || v > n) continue;
        if (u == v) continue;
        Eu.push_back(u);
        Ev.push_back(v);
        deg[u]++; deg[v]++;
    }
    size_t M = Eu.size();

    // Build CSR adjacency
    vector<int> ofs(n + 2, 0);
    for (int i = 1; i <= n; ++i) ofs[i + 1] = ofs[i] + deg[i];
    vector<int> cur = ofs;
    vector<int> adj(2 * M);
    for (size_t i = 0; i < M; ++i) {
        int u = Eu[i], v = Ev[i];
        adj[cur[u]++] = v;
        adj[cur[v]++] = u;
    }
    // Free Eu/Ev
    vector<int>().swap(Eu);
    vector<int>().swap(Ev);

    // Balance parameters
    long long ideal = (n + k - 1) / k;
    long long capLL = (long long)floor((1.0 + eps) * (double)ideal + 1e-9);
    if (capLL < 1) capLL = 1;
    int cap = (int)min<long long>(capLL, n);

    // Partition arrays
    vector<int> part(n + 1, -1);
    vector<int> partSize(k, 0);
    vector<int> capRemain(k, cap);

    // Per-part queues implemented as vectors with head indices
    vector<vector<int>> queues(k);
    vector<int> head(k, 0);
    queues.shrink_to_fit();

    // Pre-seed each part with next unassigned vertex
    int unassigned = n;
    int nextUnassigned = 1;
    for (int i = 0; i < k; ++i) {
        if (capRemain[i] <= 0) continue;
        while (nextUnassigned <= n && part[nextUnassigned] != -1) ++nextUnassigned;
        if (nextUnassigned <= n) {
            int s = nextUnassigned++;
            part[s] = i;
            partSize[i]++; capRemain[i]--; unassigned--;
            queues[i].push_back(s);
        }
    }

    // Region-growing BFS, round-robin over parts
    const int BURST = 256;
    while (unassigned > 0) {
        bool anyProgress = false;
        for (int i = 0; i < k; ++i) {
            if (capRemain[i] <= 0) { // can't grow more
                head[i] = (int)queues[i].size(); // discard remaining queued nodes
                continue;
            }
            if (head[i] >= (int)queues[i].size()) {
                // need a new seed
                while (nextUnassigned <= n && part[nextUnassigned] != -1) ++nextUnassigned;
                if (nextUnassigned <= n) {
                    int s = nextUnassigned++;
                    part[s] = i;
                    partSize[i]++; capRemain[i]--; unassigned--;
                    queues[i].push_back(s);
                    anyProgress = true;
                }
            }
            int steps = BURST;
            while (steps-- > 0 && capRemain[i] > 0 && head[i] < (int)queues[i].size()) {
                int u = queues[i][head[i]++];
                for (int e = ofs[u]; e < ofs[u + 1]; ++e) {
                    int v = adj[e];
                    if (part[v] == -1) {
                        part[v] = i;
                        partSize[i]++; capRemain[i]--; unassigned--;
                        queues[i].push_back(v);
                        anyProgress = true;
                        if (capRemain[i] == 0) break;
                    }
                }
            }
        }
        if (!anyProgress) {
            // Fallback: assign remaining vertices to any part with capacity
            for (int v = nextUnassigned; v <= n && unassigned > 0; ++v) {
                if (part[v] == -1) {
                    // find part with remaining capacity (choose min load)
                    int best = -1;
                    int bestSize = INT_MAX;
                    for (int i = 0; i < k; ++i) {
                        if (capRemain[i] > 0 && partSize[i] < bestSize) {
                            best = i;
                            bestSize = partSize[i];
                        }
                    }
                    if (best == -1) break; // shouldn't happen if capacities are sufficient
                    part[v] = best;
                    partSize[best]++; capRemain[best]--; unassigned--;
                }
            }
            break;
        }
    }

    // One pass label propagation refinement
    {
        vector<int> freq(k, 0);
        vector<int> touched;
        touched.reserve(32);
        for (int v = 1; v <= n; ++v) {
            touched.clear();
            // Count neighbor parts
            for (int e = ofs[v]; e < ofs[v + 1]; ++e) {
                int u = adj[e];
                int p = part[u];
                if (p >= 0) {
                    if (freq[p] == 0) touched.push_back(p);
                    freq[p]++;
                }
            }
            int cur = part[v];
            int curCnt = (cur >= 0 ? freq[cur] : 0);
            int best = cur;
            int bestCnt = curCnt;
            // Choose best neighboring part with capacity
            for (int p : touched) {
                if (p == cur) continue;
                if (partSize[p] >= cap) continue;
                int c = freq[p];
                if (c > bestCnt || (c == bestCnt && (best == cur || partSize[p] < partSize[best]))) {
                    best = p;
                    bestCnt = c;
                }
            }
            // Apply move if it improves local edge agreement
            if (best != cur && bestCnt > curCnt && partSize[best] + 1 <= cap) {
                partSize[cur]--;
                partSize[best]++;
                part[v] = best;
            }
            // Clear freq
            for (int p : touched) freq[p] = 0;
        }
    }

    // Output partition labels 1..k
    // Build output buffer for speed
    string out;
    out.reserve((size_t)n * 3 + n); // heuristic
    for (int i = 1; i <= n; ++i) {
        int label = part[i];
        if (label < 0) label = 0;
        int v = label + 1; // convert to 1-based
        // append integer v to out
        char buf[32];
        int len = 0;
        if (v == 0) {
            buf[len++] = '0';
        } else {
            int x = v;
            char tmp[32];
            int tlen = 0;
            while (x > 0) {
                tmp[tlen++] = char('0' + (x % 10));
                x /= 10;
            }
            while (tlen--) buf[len++] = tmp[tlen];
        }
        out.append(buf, buf + len);
        if (i < n) out.push_back(' ');
    }
    out.push_back('\n');
    fwrite(out.c_str(), 1, out.size(), stdout);
    return 0;
}