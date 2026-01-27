#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static const int BUFSIZE = 1 << 20;
    int idx, size;
    char buf[BUFSIZE];
    FastScanner(): idx(0), size(0) {}
    inline char getChar() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return EOF;
        }
        return buf[idx++];
    }
    template<typename T>
    bool nextInt(T &out) {
        char c;
        T sign = 1;
        T val = 0;
        c = getChar();
        if (c == EOF) return false;
        while (c != '-' && (c < '0' || c > '9')) {
            c = getChar();
            if (c == EOF) return false;
        }
        if (c == '-') { sign = -1; c = getChar(); }
        for (; c >= '0' && c <= '9'; c = getChar()) {
            val = val * 10 + (c - '0');
        }
        out = val * sign;
        return true;
    }
};

static void pruneCover(vector<char>& cover, const vector<vector<int>>& inc, const vector<int>& U, const vector<int>& V) {
    int N = (int)cover.size();
    for (int v = 0; v < N; ++v) {
        if (!cover[v]) continue;
        bool removable = true;
        for (int idx : inc[v]) {
            int w = (U[idx] == v) ? V[idx] : U[idx];
            if (!cover[w]) { removable = false; break; }
        }
        if (removable) cover[v] = 0;
    }
}

static vector<char> maximalMatchingCover(int N, int M, const vector<int>& U, const vector<int>& V, const vector<vector<int>>& inc) {
    vector<char> used(N, 0), cover(N, 0);
    for (int i = 0; i < M; ++i) {
        int u = U[i], v = V[i];
        if (!used[u] && !used[v]) {
            used[u] = used[v] = 1;
            cover[u] = cover[v] = 1;
        }
    }
    pruneCover(cover, inc, U, V);
    return cover;
}

static vector<char> degreeGreedyCover(int N, int M, const vector<int>& U, const vector<int>& V, const vector<vector<int>>& inc) {
    vector<int> residdeg(N);
    for (int i = 0; i < N; ++i) residdeg[i] = (int)inc[i].size();
    vector<char> covered(M, 0), cover(N, 0);
    int remaining = M;
    priority_queue<pair<int,int>> pq;
    for (int i = 0; i < N; ++i) pq.push({residdeg[i], i});
    while (remaining > 0) {
        while (!pq.empty()) {
            auto [d, v] = pq.top();
            if (d != residdeg[v] || cover[v] || d == 0) { pq.pop(); continue; }
            // pick v
            cover[v] = 1;
            for (int ei : inc[v]) {
                if (!covered[ei]) {
                    covered[ei] = 1;
                    --remaining;
                    int w = (U[ei] == v) ? V[ei] : U[ei];
                    if (residdeg[w] > 0) {
                        --residdeg[w];
                        pq.push({residdeg[w], w});
                    }
                }
            }
            residdeg[v] = 0;
            break;
        }
        if (pq.empty() && remaining > 0) {
            // Fallback: pick an endpoint of any uncovered edge
            for (int i = 0; i < M && remaining > 0; ++i) {
                if (!covered[i]) {
                    int v = U[i];
                    if (!cover[v]) {
                        cover[v] = 1;
                        for (int ei : inc[v]) {
                            if (!covered[ei]) {
                                covered[ei] = 1;
                                --remaining;
                                int w = (U[ei] == v) ? V[ei] : U[ei];
                                if (residdeg[w] > 0) {
                                    --residdeg[w];
                                }
                            }
                        }
                        residdeg[v] = 0;
                    }
                    break;
                }
            }
        }
    }
    pruneCover(cover, inc, U, V);
    return cover;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    int N, M;
    if (!fs.nextInt(N)) return 0;
    fs.nextInt(M);
    vector<int> U(M), V(M);
    vector<vector<int>> inc(N);
    for (int i = 0; i < M; ++i) {
        int u, v;
        fs.nextInt(u);
        fs.nextInt(v);
        --u; --v;
        U[i] = u; V[i] = v;
        inc[u].push_back(i);
        inc[v].push_back(i);
    }

    vector<char> cover1 = maximalMatchingCover(N, M, U, V, inc);
    vector<char> cover2 = degreeGreedyCover(N, M, U, V, inc);

    int k1 = 0, k2 = 0;
    for (int i = 0; i < N; ++i) { k1 += cover1[i]; k2 += cover2[i]; }

    vector<char>& best = (k1 <= k2) ? cover1 : cover2;

    string out;
    out.reserve(N * 2);
    for (int i = 0; i < N; ++i) {
        out.push_back(best[i] ? '1' : '0');
        out.push_back('\n');
    }
    fwrite(out.c_str(), 1, out.size(), stdout);
    return 0;
}