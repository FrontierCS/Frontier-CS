#include <bits/stdc++.h>
using namespace std;

static bool readBinaryRow(int n, string &out) {
    out.clear();
    out.reserve(n);
    char ch;
    while ((int)out.size() < n) {
        if (!cin.get(ch)) return false;
        if (ch == '0' || ch == '1') out.push_back(ch);
    }
    return true;
}

static bool isValidPermutation(const vector<int> &p, const vector<string> &mat) {
    int n = (int)p.size();
    vector<char> seen(n + 1, 0);
    for (int x : p) {
        if (x < 1 || x > n || seen[x]) return false;
        seen[x] = 1;
    }
    vector<int> c(n);
    for (int i = 0; i < n - 1; i++) c[i] = mat[p[i] - 1][p[i + 1] - 1] - '0';
    c[n - 1] = mat[p[n - 1] - 1][p[0] - 1] - '0';
    int changes = 0;
    for (int i = 0; i < n - 1; i++) changes += (c[i] != c[i + 1]);
    return changes <= 1;
}

static vector<int> rotateCycle(const vector<int> &cyc, int start) {
    int n = (int)cyc.size();
    vector<int> p(n);
    for (int i = 0; i < n; i++) p[i] = cyc[(start + i) % n];
    return p;
}

static void considerCandidatesFromCycle(
    const vector<int> &cyc,
    const vector<string> &mat,
    vector<int> &best,
    bool &hasBest
) {
    int n = (int)cyc.size();
    auto col = [&](int u, int v) -> int { return mat[u - 1][v - 1] - '0'; };

    vector<int> e(n);
    for (int i = 0; i < n; i++) e[i] = col(cyc[i], cyc[(i + 1) % n]);

    vector<int> diffIdx;
    for (int i = 0; i < n; i++) {
        if (e[i] != e[(i + 1) % n]) diffIdx.push_back(i);
    }

    vector<int> starts;
    if (diffIdx.empty()) {
        int mn = cyc[0], idx = 0;
        for (int i = 1; i < n; i++) if (cyc[i] < mn) mn = cyc[i], idx = i;
        starts.push_back(idx);
    } else {
        for (int i : diffIdx) starts.push_back((i + 1) % n);
    }

    for (int st : starts) {
        vector<int> p = rotateCycle(cyc, st);
        if (!isValidPermutation(p, mat)) continue;
        if (!hasBest || p < best) {
            best = std::move(p);
            hasBest = true;
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    while (cin >> n) {
        vector<string> mat(n);
        for (int i = 0; i < n; i++) {
            if (!readBinaryRow(n, mat[i])) return 0;
        }
        auto col = [&](int u, int v) -> int { return mat[u - 1][v - 1] - '0'; };

        int shared = 1;
        deque<int> A, B; // from free end (front) to shared (back); both end at shared
        A.push_back(shared);
        B.push_back(shared);

        for (int v = 2; v <= n; v++) {
            while (true) {
                int a = A.front();
                int b = B.front();

                if (col(v, a) == 0) {
                    A.push_front(v);
                    break;
                }
                if (col(v, b) == 1) {
                    B.push_front(v);
                    break;
                }

                // col(v,a)=1 and col(v,b)=0
                int t = col(a, b);
                if (t == 0) {
                    if (B.size() > 1) {
                        int x = B.front();
                        B.pop_front();
                        A.push_front(x);
                        A.push_front(v);
                        break;
                    } else {
                        // reroot to a
                        shared = a;
                        std::reverse(A.begin(), A.end());
                        B.clear();
                        B.push_back(shared);
                        continue;
                    }
                } else {
                    if (A.size() > 1) {
                        int x = A.front();
                        A.pop_front();
                        B.push_front(x);
                        B.push_front(v);
                        break;
                    } else {
                        // reroot to b
                        shared = b;
                        std::reverse(B.begin(), B.end());
                        A.clear();
                        A.push_back(shared);
                        continue;
                    }
                }
            }
        }

        // Build cycle: A (front->back includes shared) then reverse(B excluding shared)
        vector<int> cyc;
        cyc.reserve(n);
        for (int x : A) cyc.push_back(x);
        if (B.size() > 1) {
            for (int i = (int)B.size() - 2; i >= 0; --i) cyc.push_back(B[i]);
        }

        vector<int> best;
        bool hasBest = false;

        considerCandidatesFromCycle(cyc, mat, best, hasBest);
        vector<int> cycRev = cyc;
        reverse(cycRev.begin(), cycRev.end());
        considerCandidatesFromCycle(cycRev, mat, best, hasBest);

        if (!hasBest) {
            // Fallback: try as-is
            if (isValidPermutation(cyc, mat)) {
                best = cyc;
                hasBest = true;
            }
        }

        if (!hasBest) {
            cout << -1 << "\n";
            continue;
        }

        for (int i = 0; i < n; i++) {
            if (i) cout << ' ';
            cout << best[i];
        }
        cout << "\n";
    }
    return 0;
}