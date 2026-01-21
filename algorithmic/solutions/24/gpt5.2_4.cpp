#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static constexpr int BUFSIZE = 1 << 20;
    int idx = 0, size = 0;
    char buf[BUFSIZE];

    inline char readChar() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }

    bool readInt(int &out) {
        char c;
        do {
            c = readChar();
            if (!c) return false;
        } while (c <= ' ');
        int sign = 1;
        if (c == '-') {
            sign = -1;
            c = readChar();
        }
        int x = 0;
        while (c > ' ') {
            x = x * 10 + (c - '0');
            c = readChar();
        }
        out = x * sign;
        return true;
    }

    bool readBinaryRow(int n, string &row) {
        row.clear();
        row.reserve(n);
        while ((int)row.size() < n) {
            char c = readChar();
            if (!c) return false;
            if (c == '0' || c == '1') row.push_back(c);
        }
        return true;
    }
};

static inline bool lexLessVec(const vector<int> &a, const vector<int> &b) {
    int n = (int)a.size();
    for (int i = 0; i < n; i++) {
        if (a[i] != b[i]) return a[i] < b[i];
    }
    return false;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    int n;
    string out;
    out.reserve(1 << 20);

    while (fs.readInt(n)) {
        vector<string> C(n);
        for (int i = 0; i < n; i++) {
            if (!fs.readBinaryRow(n, C[i])) return 0;
        }

        auto getc = [&](int u, int v) -> char { return C[u][v]; };

        vector<int> p0, p1;
        p0.reserve(n);
        p1.reserve(n);

        for (int v = 0; v < n; v++) {
            if (p0.empty()) {
                p0.push_back(v);
            } else if (getc(p0.back(), v) == '0') {
                p0.push_back(v);
            } else if (p1.empty()) {
                p1.push_back(v);
            } else if (getc(p1.back(), v) == '1') {
                p1.push_back(v);
            } else {
                int a = p0.back();
                int b = p1.back();
                if (getc(a, b) == '0') {
                    int u = p1.back();
                    p1.pop_back();
                    p0.push_back(u);
                    p0.push_back(v);
                } else {
                    int u = p0.back();
                    p0.pop_back();
                    p1.push_back(u);
                    p1.push_back(v);
                }
            }
        }

        auto makeCycle = [&](const vector<int> &a, const vector<int> &b) -> vector<int> {
            vector<int> q;
            q.reserve(n);
            q.insert(q.end(), a.begin(), a.end());
            for (int i = (int)b.size(); i-- > 0;) q.push_back(b[i]);
            return q;
        };

        vector<vector<int>> cycles;
        cycles.reserve(4);
        cycles.push_back(makeCycle(p0, p1));
        cycles.push_back(makeCycle(p1, p0));
        for (int k = 0; k < 2; k++) {
            vector<int> r = cycles[k];
            reverse(r.begin(), r.end());
            cycles.push_back(std::move(r));
        }

        auto bestRotationForCycle = [&](const vector<int> &q) -> vector<int> {
            int N = (int)q.size();

            auto isValid = [&](int s) -> bool {
                int cnt = 0;
                char prev = getc(q[s], q[(s + 1) % N]);
                for (int i = 1; i < N; i++) {
                    int u = q[(s + i) % N];
                    int v = q[(s + i + 1) % N];
                    char cur = getc(u, v);
                    if (cur != prev) {
                        cnt++;
                        if (cnt > 1) return false;
                    }
                    prev = cur;
                }
                return true;
            };

            auto lessRot = [&](int s, int t) -> bool {
                for (int i = 0; i < N; i++) {
                    int a = q[(s + i) % N];
                    int b = q[(t + i) % N];
                    if (a != b) return a < b;
                }
                return false;
            };

            int bestStart = -1;
            for (int s = 0; s < N; s++) {
                if (!isValid(s)) continue;
                if (bestStart == -1 || lessRot(s, bestStart)) bestStart = s;
            }
            if (bestStart == -1) return {};

            vector<int> ans;
            ans.reserve(N);
            for (int i = 0; i < N; i++) ans.push_back(q[(bestStart + i) % N] + 1);
            return ans;
        };

        vector<int> best;
        for (const auto &q : cycles) {
            vector<int> cand = bestRotationForCycle(q);
            if (cand.empty()) continue;
            if (best.empty() || lexLessVec(cand, best)) best = std::move(cand);
        }

        if (best.empty()) {
            out += "-1\n";
        } else {
            for (int i = 0; i < n; i++) {
                if (i) out.push_back(' ');
                out += to_string(best[i]);
            }
            out.push_back('\n');
        }
    }

    fwrite(out.c_str(), 1, out.size(), stdout);
    return 0;
}