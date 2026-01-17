#include <bits/stdc++.h>
using namespace std;

int N, M;
int queries = 0;

int query(vector<int> v) {
    queries++;
    cout << "Query " << v.size();
    for (int x : v) cout << " " << x;
    cout << endl;
    int res;
    cin >> res;
    return res;
}

void answer(int a, int b) {
    cout << "Answer " << a << " " << b << endl;
}

// Find a neighbor of u among candidates, excluding prev.
// Uses reference r which is assumed same gender as u, and not in candidates.
int find_neighbor(int u, int prev, vector<int>& candidates, int r) {
    if (candidates.empty()) return -1;
    int lo = 0, hi = (int)candidates.size() - 1;
    while (lo < hi) {
        int mid = (lo + hi) / 2;
        vector<int> L;
        for (int i = lo; i <= mid; i++) L.push_back(candidates[i]);
        vector<int> A = L;
        A.push_back(r);
        int da = query(A);
        vector<int> B = A;
        B.push_back(u);
        int db = query(B);
        if (db == da) {
            hi = mid;
        } else {
            lo = mid + 1;
        }
    }
    int cand = candidates[lo];
    if (query({u, cand}) == 1) {
        return cand;
    } else {
        return -1;
    }
}

int main() {
    cin >> N;
    M = 2 * N;
    vector<bool> visited(M + 1, false);
    vector<pair<int, int>> color_edges;

    for (int start = 1; start <= M; ++start) {
        if (visited[start]) continue;

        int neighbor1 = -1;
        for (int j = 1; j <= M; ++j) {
            if (j == start || visited[j]) continue;
            if (query({start, j}) == 1) {
                neighbor1 = j;
                break;
            }
        }
        if (neighbor1 == -1) continue;

        vector<int> cycle;
        cycle.push_back(start);
        cycle.push_back(neighbor1);
        visited[start] = visited[neighbor1] = true;

        int prev = start;
        int cur = neighbor1;

        while (true) {
            vector<int> candidates;
            for (int v = 1; v <= M; ++v) {
                if (!visited[v] && v != cur && v != prev) {
                    candidates.push_back(v);
                }
            }

            if (query({cur, start}) == 1 && prev != start) {
                cycle.push_back(start);
                break;
            }

            int ref = -1;
            if (cycle.size() >= 3) {
                int parity = (cycle.size() - 1) % 2;
                if (parity == 0) {
                    ref = cycle[0];
                } else {
                    ref = cycle[1];
                }
            }

            int next = -1;
            if (ref != -1 && !candidates.empty()) {
                next = find_neighbor(cur, prev, candidates, ref);
            }
            if (next == -1) {
                for (int cand : candidates) {
                    if (query({cur, cand}) == 1) {
                        next = cand;
                        break;
                    }
                }
            }
            if (next == -1) break;
            if (next == start) break;

            cycle.push_back(next);
            visited[next] = true;
            prev = cur;
            cur = next;
        }

        int L = cycle.size();
        if (L < 3) continue;

        int res = query({cycle[0], cycle[1], cycle[2]});
        bool first_is_love = (res == 1);

        for (int i = 0; i < L; i += 2) {
            int idx = i;
            if (first_is_love) idx = i + 1;
            if (idx >= L) continue;
            int a = cycle[idx];
            int b = cycle[(idx + 1) % L];
            color_edges.push_back({min(a, b), max(a, b)});
        }
    }

    for (auto p : color_edges) {
        answer(p.first, p.second);
    }

    return 0;
}