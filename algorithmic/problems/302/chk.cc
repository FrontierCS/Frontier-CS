#include <cmath>
#include <algorithm>

// Keep historical scores through 60; above the anchor, compare physical objectives.
static double natural_log_score(long double old_points, long double value,
                                long double anchor, bool minimize) {
    if (minimize && value == 0.0L) return 100.0;
    if (old_points <= 60.0L) return (double)std::max(0.0L, old_points);
    if (!(value > 0.0L) || !(anchor > 0.0L))
        return (double)std::clamp(old_points, 0.0L, 100.0L);
    const long double improvement = minimize
        ? std::log(anchor) - std::log(value)
        : std::log(value) - std::log(anchor);
    return (double)std::clamp(60.0L + improvement, 0.0L, 100.0L);
}


#include <algorithm>
// Historical bounded base ratio; only its <=60-point branch is retained.
static double bounded_base_ratio(double s) {
    return std::max(0.0, std::min(1.0, s));
}

#include "testlib.h"
#include <bits/stdc++.h>
using namespace std;

static inline int chId(char c) { return c - 'a'; }

struct AhoCorasick {
    int K; // alphabet size (first K letters)
    struct Node {
        array<int, 26> nxt;
        int link = 0;
        long long outW = 0; // sum of weights of patterns ending here (after propagation)
        Node() { nxt.fill(-1); }
    };

    vector<Node> t;

    explicit AhoCorasick(int K_) : K(K_) {
        t.reserve(1);
        t.push_back(Node()); // root
    }

    void addPattern(const string& s, long long w) {
        int v = 0;
        for (char cc : s) {
            int c = chId(cc);
            if (c < 0 || c >= K) continue; // input guaranteed valid; keep safe
            if (t[v].nxt[c] == -1) {
                t[v].nxt[c] = (int)t.size();
                t.push_back(Node());
            }
            v = t[v].nxt[c];
        }
        t[v].outW += w;
    }

    void build() {
        queue<int> q;
        // init root transitions
        for (int c = 0; c < K; c++) {
            int u = t[0].nxt[c];
            if (u != -1) {
                t[u].link = 0;
                q.push(u);
            } else {
                t[0].nxt[c] = 0;
            }
        }

        while (!q.empty()) {
            int v = q.front(); q.pop();
            int lk = t[v].link;
            t[v].outW += t[lk].outW; // propagate outputs

            for (int c = 0; c < K; c++) {
                int u = t[v].nxt[c];
                if (u != -1) {
                    t[u].link = t[lk].nxt[c];
                    q.push(u);
                } else {
                    t[v].nxt[c] = t[lk].nxt[c];
                }
            }
        }
    }

    long long scoreMotifs(const string& s) const {
        long long res = 0;
        int v = 0;
        for (char cc : s) {
            int c = chId(cc);
            if (c < 0 || c >= K) continue; // invalid chars handled elsewhere
            v = t[v].nxt[c];
            res += t[v].outW;
        }
        return res;
    }
};

static long long computePenalty(
    const string& s,
    int k,
    const vector<vector<long long>>& W,
    const AhoCorasick& ac
) {
    long long big = 0;
    for (int i = 0; i + 1 < (int)s.size(); i++) {
        int a = chId(s[i]);
        int b = chId(s[i + 1]);
        if (a < 0 || a >= k || b < 0 || b >= k) return (long long)4e18; // invalid
        big += W[a][b];
    }
    long long mot = ac.scoreMotifs(s);
    return big + mot;
}

static string buildBaseline(int n, int k, const vector<int>& cnt) {
    string s;
    s.reserve(n);
    for (int i = 0; i < k; i++) s.append(cnt[i], char('a' + i));
    return s;
}

int main(int argc, char* argv[]) {
    registerTestlibCmd(argc, argv);

    int n = inf.readInt();
    int k = inf.readInt();
    vector<int> cnt(k);
    long long sum = 0;
    for (int i = 0; i < k; i++) { cnt[i] = inf.readInt(); sum += cnt[i]; }
    if (sum != n) quitf(_fail, "Input invalid: sum ci != n");

    vector<vector<long long>> W(k, vector<long long>(k));
    for (int i = 0; i < k; i++)
        for (int j = 0; j < k; j++)
            W[i][j] = inf.readLong();

    int m = inf.readInt();
    AhoCorasick ac(k);
    for (int i = 0; i < m; i++) {
        string p = inf.readToken();
        long long w = inf.readLong();
        ac.addPattern(p, w);
    }
    ac.build();

    // Build the single deterministic baseline described in the statement.
    string sBase = buildBaseline(n, k, cnt);
    long long B = computePenalty(sBase, k, W, ac);

    // Read participant output
    string out;
    if (!ouf.seekEof()) out = ouf.readToken();
    // Allow trailing spaces/newlines; ensure no extra tokens
    if (!ouf.seekEof()) {
        // if there are more tokens, consider WA (ambiguous output format)
        quitp(0.0, "Extra tokens in output");
    }

    auto quitZero = [&](const char* msg) {
        quitp(0.0, "%s", msg);
    };

    if ((int)out.size() != n) quitZero("Infeasible: wrong length");

    vector<int> got(k, 0);
    for (char c : out) {
        int id = chId(c);
        if (id < 0 || id >= k) quitZero("Infeasible: character outside alphabet");
        got[id]++;
    }
    for (int i = 0; i < k; i++) {
        if (got[i] != cnt[i]) quitZero("Infeasible: wrong letter counts");
    }

    long long X = computePenalty(out, k, W, ac);

    long long denomLL = max(1LL, B);
    long double ratio = (long double)(B - X) / (long double)denomLL;
    if (ratio < 0) ratio = 0;
    if (ratio > 1) ratio = 1;

    ratio = bounded_base_ratio((double)ratio);
    ratio = natural_log_score(100.0L * (ratio), X, B-0.6L*denomLL, true) / 100.0;
    quitp((double)ratio, "Ratio: %.12Lf B=%lld X=%lld denom=%lld", ratio, B, X, denomLL);
}
