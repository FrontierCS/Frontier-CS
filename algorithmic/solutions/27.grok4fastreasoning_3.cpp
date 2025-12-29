#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, m;
    cin >> n >> m;
    bool swapped = false;
    if (n > m) {
        swap(n, m);
        swapped = true;
    }
    int N = n, M = m;
    double sq = sqrt(M);
    int target_d = min(M, (int)(M / (double)N + sq));
    vector<vector<int>> sets(N);
    vector<vector<int>> col_rows(M + 1);
    vector<int> cover_count(M + 1, 0);
    for (int r = 0; r < N; r++) {
        vector<char> forbidden(M + 1, 0);
        vector<int> S;
        int rem = target_d;
        // add uncovered
        for (int j = 1; j <= M && rem > 0; j++) {
            if (cover_count[j] == 0 && !forbidden[j]) {
                S.push_back(j);
                rem--;
            }
        }
        // add covered, from high to low
        for (int j = M; j >= 1 && rem > 0; j--) {
            if (cover_count[j] > 0 && !forbidden[j]) {
                S.push_back(j);
                rem--;
                // mark neighbors
                for (int prev : col_rows[j]) {
                    for (int v : sets[prev]) {
                        forbidden[v] = 1;
                    }
                }
            }
        }
        sets[r] = S;
        // update
        for (int j : S) {
            col_rows[j].push_back(r);
            cover_count[j]++;
        }
    }
    vector<pair<int, int>> points;
    for (int r = 0; r < N; r++) {
        for (int c : sets[r]) {
            if (swapped) {
                points.emplace_back(c, r + 1);
            } else {
                points.emplace_back(r + 1, c);
            }
        }
    }
    cout << points.size() << endl;
    for (auto& p : points) {
        cout << p.first << " " << p.second << endl;
    }
    return 0;
}