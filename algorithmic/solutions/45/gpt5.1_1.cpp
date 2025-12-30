#include <cstdio>
#include <vector>
#include <algorithm>
#include <random>
#include <cmath>
#include <cstdlib>

using namespace std;

struct FastScanner {
    static const int BUFSIZE = 1 << 20;
    int idx, size;
    char buf[BUFSIZE];

    FastScanner() : idx(0), size(0) {}

    inline char getChar() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0; // EOF
        }
        return buf[idx++];
    }

    bool nextInt(int &x) {
        char c;
        do {
            c = getChar();
            if (!c) return false;
        } while (c <= ' ');
        int neg = 0;
        if (c == '-') {
            neg = 1;
            c = getChar();
        }
        int val = 0;
        while (c >= '0' && c <= '9') {
            val = val * 10 + (c - '0');
            c = getChar();
        }
        x = neg ? -val : val;
        return true;
    }

    bool nextToken(char *s) {
        char c;
        do {
            c = getChar();
            if (!c) {
                *s = 0;
                return false;
            }
        } while (c <= ' ');
        int len = 0;
        while (c > ' ') {
            s[len++] = c;
            c = getChar();
            if (!c) break;
        }
        s[len] = 0;
        return true;
    }
};

struct FastOutput {
    static const int BUFSIZE = 1 << 20;
    int idx;
    char buf[BUFSIZE];

    FastOutput() : idx(0) {}
    ~FastOutput() { flush(); }

    inline void flush() {
        if (idx) {
            fwrite(buf, 1, idx, stdout);
            idx = 0;
        }
    }

    inline void putChar(char c) {
        if (idx >= BUFSIZE) flush();
        buf[idx++] = c;
    }

    inline void writeInt(int x, char end) {
        if (x == 0) {
            if (idx + 2 > BUFSIZE) flush();
            buf[idx++] = '0';
            buf[idx++] = end;
            return;
        }
        if (x < 0) {
            if (idx + 1 > BUFSIZE) flush();
            buf[idx++] = '-';
            x = -x;
        }
        char s[12];
        int n = 0;
        while (x > 0) {
            s[n++] = char('0' + (x % 10));
            x /= 10;
        }
        if (idx + n + 1 > BUFSIZE) flush();
        for (int i = n - 1; i >= 0; --i) buf[idx++] = s[i];
        buf[idx++] = end;
    }
};

int main() {
    FastScanner fs;

    int n, m, k;
    char epsBuf[64];

    if (!fs.nextInt(n)) return 0;
    fs.nextInt(m);
    fs.nextInt(k);
    fs.nextToken(epsBuf);
    double eps = atof(epsBuf);

    vector<vector<int>> g;
    g.resize(n + 1);

    for (int i = 0; i < m; ++i) {
        int u, v;
        if (!fs.nextInt(u)) break;
        fs.nextInt(v);
        if (u == v) continue; // ignore self-loops to save a bit
        if (u >= 1 && u <= n && v >= 1 && v <= n) {
            g[u].push_back(v);
            g[v].push_back(u);
        }
    }

    long long ideal = (n + (long long)k - 1) / (long long)k;
    long double cap_ld = (1.0L + (long double)eps) * (long double)ideal;
    long long cap = (long long)floor(cap_ld + 1e-12L);

    if (cap < ideal) cap = ideal; // safety, though eps > 0 in dataset

    vector<int> part(n + 1, 0);
    vector<int> partSize(k + 1, 0);
    vector<int> q;
    q.reserve(n);

    int assigned = 0;
    int cur = 1;

    // BFS-based growing partition
    for (int pid = 1; pid <= k && assigned < n; ++pid) {
        if (assigned >= n) break;

        // find first unassigned seed
        while (cur <= n && part[cur] != 0) ++cur;
        if (cur > n) break;

        q.clear();
        part[cur] = pid;
        partSize[pid]++;
        assigned++;
        q.push_back(cur);

        size_t qhead = 0;
        while (partSize[pid] < cap && assigned < n) {
            if (qhead < q.size()) {
                int u = q[qhead++];
                const auto &adj = g[u];
                for (int v : adj) {
                    if (part[v] == 0) {
                        part[v] = pid;
                        partSize[pid]++;
                        assigned++;
                        q.push_back(v);
                        if (partSize[pid] >= cap) break;
                    }
                }
            } else {
                // queue empty but still room: start from a new seed
                while (cur <= n && part[cur] != 0) ++cur;
                if (cur > n) break;
                part[cur] = pid;
                partSize[pid]++;
                assigned++;
                q.push_back(cur);
            }
        }
    }

    // Fallback in the unlikely event some vertices remain (shouldn't happen)
    if (assigned < n) {
        int lastPart = k;
        for (int i = 1; i <= n; ++i) {
            if (part[i] == 0) {
                if (partSize[lastPart] >= cap) {
                    // find any part with room
                    for (int p = 1; p <= k; ++p) {
                        if (partSize[p] < cap) {
                            lastPart = p;
                            break;
                        }
                    }
                }
                part[i] = lastPart;
                partSize[lastPart]++;
                assigned++;
            }
        }
    }

    // Optional local refinement to reduce edge cut (only for not-too-large graphs)
    if (k > 1 && n <= 2000000) {
        int iterations = 1;
        if (n <= 100000) iterations = 3;
        else if (n <= 500000) iterations = 2;

        vector<int> countPart(k + 1, 0);
        vector<int> touched;
        touched.reserve(32);

        vector<int> order(n);
        for (int i = 0; i < n; ++i) order[i] = i + 1;

        if (n <= 1000000) {
            mt19937 rng(712367821);
            shuffle(order.begin(), order.end(), rng);
        }

        for (int it = 0; it < iterations; ++it) {
            if (it > 0 && n <= 1000000) {
                mt19937 rng(712367821 + it);
                shuffle(order.begin(), order.end(), rng);
            }
            for (int idx = 0; idx < n; ++idx) {
                int u = order[idx];
                int oldP = part[u];
                const auto &adj = g[u];
                if (adj.empty()) continue;

                touched.clear();
                for (int v : adj) {
                    int qid = part[v];
                    if (countPart[qid] == 0) touched.push_back(qid);
                    countPart[qid]++;
                }

                int bestP = oldP;
                int bestSame = countPart[oldP];
                for (int qid : touched) {
                    if (qid == oldP) continue;
                    int same = countPart[qid];
                    if (same > bestSame && partSize[qid] < cap) {
                        bestSame = same;
                        bestP = qid;
                    }
                }

                if (bestP != oldP) {
                    part[u] = bestP;
                    partSize[oldP]--;
                    partSize[bestP]++;
                }

                for (int qid : touched) countPart[qid] = 0;
            }
        }
    }

    FastOutput fo;
    for (int i = 1; i <= n; ++i) {
        char end = (i == n) ? '\n' : ' ';
        fo.writeInt(part[i], end);
    }

    return 0;
}