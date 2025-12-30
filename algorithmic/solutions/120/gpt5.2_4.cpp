#include <bits/stdc++.h>
using namespace std;

static const int N = 100;

static int ask(int a, int b, int c) {
    cout << "? " << a << " " << b << " " << c << endl;
    cout.flush();
    int x;
    if (!(cin >> x)) exit(0);
    if (x < 0) exit(0);
    return x;
}

struct Candidate {
    array<bitset<N + 1>, N + 1> adj; // 1..100
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int q123 = ask(1, 2, 3);

    vector<int> q12(N + 1, -1), q13(N + 1, -1), q23(N + 1, -1);
    for (int i = 4; i <= N; i++) {
        q12[i] = ask(1, 2, i);
        q13[i] = ask(1, 3, i);
        q23[i] = ask(2, 3, i);
    }

    vector<vector<int>> q1uv(N + 1, vector<int>(N + 1, -1));
    for (int u = 4; u <= N; u++) {
        for (int v = u + 1; v <= N; v++) {
            q1uv[u][v] = ask(1, u, v);
        }
    }

    vector<tuple<int,int,int>> base;
    for (int e12 = 0; e12 <= 1; e12++) {
        for (int e13 = 0; e13 <= 1; e13++) {
            for (int e23 = 0; e23 <= 1; e23++) {
                if (e12 + e13 + e23 == q123) base.emplace_back(e12, e13, e23);
            }
        }
    }

    vector<Candidate> candidates;
    candidates.reserve(3);

    for (auto [e12, e13, e23] : base) {
        vector<int> e1(N + 1, 0), e2(N + 1, 0), e3(N + 1, 0);
        e1[2] = e12; e1[3] = e13;
        e2[1] = e12; e2[3] = e23;
        e3[1] = e13; e3[2] = e23;

        bool ok = true;

        for (int i = 4; i <= N; i++) {
            int s12 = q12[i] - e12;
            int s13 = q13[i] - e13;
            int s23 = q23[i] - e23;
            if (!(0 <= s12 && s12 <= 2 && 0 <= s13 && s13 <= 2 && 0 <= s23 && s23 <= 2)) { ok = false; break; }

            int n1 = s12 + s13 - s23;
            int n2 = s12 + s23 - s13;
            int n3 = s13 + s23 - s12;
            if ((n1 & 1) || (n2 & 1) || (n3 & 1)) { ok = false; break; }
            int x = n1 / 2, y = n2 / 2, z = n3 / 2;
            if (!(0 <= x && x <= 1 && 0 <= y && y <= 1 && 0 <= z && z <= 1)) { ok = false; break; }
            if (x + y != s12 || x + z != s13 || y + z != s23) { ok = false; break; }

            e1[i] = x; e2[i] = y; e3[i] = z;
        }
        if (!ok) continue;

        Candidate cand;
        for (int i = 1; i <= N; i++) cand.adj[i].reset();

        auto setEdge = [&](int u, int v, int val) {
            if (u == v) return;
            if (val) { cand.adj[u].set(v); cand.adj[v].set(u); }
            else { cand.adj[u].reset(v); cand.adj[v].reset(u); }
        };

        setEdge(1, 2, e12);
        setEdge(1, 3, e13);
        setEdge(2, 3, e23);

        for (int i = 4; i <= N; i++) {
            setEdge(1, i, e1[i]);
            setEdge(2, i, e2[i]);
            setEdge(3, i, e3[i]);
        }

        for (int u = 4; u <= N; u++) {
            for (int v = u + 1; v <= N; v++) {
                int r = q1uv[u][v];
                int ev = r - e1[u] - e1[v];
                if (!(ev == 0 || ev == 1)) { ok = false; break; }
                setEdge(u, v, ev);
            }
            if (!ok) break;
        }
        if (!ok) continue;

        candidates.push_back(cand);
    }

    auto triSum = [&](const Candidate& cand, int a, int b, int c) -> int {
        return (int)cand.adj[a].test(b) + (int)cand.adj[a].test(c) + (int)cand.adj[b].test(c);
    };

    auto sameGraph = [&](const Candidate& A, const Candidate& B) -> bool {
        for (int i = 1; i <= N; i++) if (A.adj[i] != B.adj[i]) return false;
        return true;
    };

    while (candidates.size() > 1) {
        bool allSame = true;
        for (size_t i = 1; i < candidates.size(); i++) {
            if (!sameGraph(candidates[0], candidates[i])) { allSame = false; break; }
        }
        if (allSame) break;

        bool found = false;
        int qa = -1, qb = -1, qc = -1;

        for (int i = 4; i <= N && !found; i++) {
            for (int j = i + 1; j <= N && !found; j++) {
                int s0 = triSum(candidates[0], 2, i, j);
                bool diff = false;
                for (size_t k = 1; k < candidates.size(); k++) {
                    if (triSum(candidates[k], 2, i, j) != s0) { diff = true; break; }
                }
                if (diff) {
                    qa = 2; qb = i; qc = j;
                    found = true;
                }
            }
        }

        for (int i = 4; i <= N && !found; i++) {
            for (int j = i + 1; j <= N && !found; j++) {
                int s0 = triSum(candidates[0], 3, i, j);
                bool diff = false;
                for (size_t k = 1; k < candidates.size(); k++) {
                    if (triSum(candidates[k], 3, i, j) != s0) { diff = true; break; }
                }
                if (diff) {
                    qa = 3; qb = i; qc = j;
                    found = true;
                }
            }
        }

        if (!found) break;

        int ans = ask(qa, qb, qc);
        vector<Candidate> filtered;
        for (auto &cand : candidates) {
            if (triSum(cand, qa, qb, qc) == ans) filtered.push_back(cand);
        }
        candidates.swap(filtered);

        if (candidates.empty()) break;
    }

    Candidate finalCand;
    if (!candidates.empty()) finalCand = candidates[0];
    else {
        // Fallback: output empty graph (should never happen with correct interaction)
        for (int i = 1; i <= N; i++) finalCand.adj[i].reset();
    }

    cout << "!" << endl;
    for (int i = 1; i <= N; i++) {
        string s;
        s.reserve(N);
        for (int j = 1; j <= N; j++) {
            if (i == j) s.push_back('0');
            else s.push_back(finalCand.adj[i].test(j) ? '1' : '0');
        }
        cout << s << "\n";
    }
    cout.flush();
    return 0;
}