#include <bits/stdc++.h>
using namespace std;

int main() {
    const int N = 20;
    vector<vector<int>> h(N, vector<int>(N));
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            cin >> h[i][j];
        }
    }

    int x = 0, y = 0;
    long long load = 0;
    vector<string> ans;

    auto all_zero = [&]() {
        for (int i = 0; i < N; ++i)
            for (int j = 0; j < N; ++j)
                if (h[i][j] != 0) return false;
        return true;
    };

    while (!all_zero()) {
        // load if positive
        if (h[x][y] > 0) {
            int d = h[x][y];
            ans.push_back("+" + to_string(d));
            load += d;
            h[x][y] = 0;
            continue;
        }
        // unload if negative and have enough load
        if (h[x][y] < 0 && load >= -h[x][y]) {
            int d = -h[x][y];
            ans.push_back("-" + to_string(d));
            load -= d;
            h[x][y] = 0;
            continue;
        }

        // find nearest available cell
        int best_dist = INT_MAX;
        int best_i = -1, best_j = -1;
        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < N; ++j) {
                if (h[i][j] == 0) continue;
                if (h[i][j] > 0) {
                    int dist = abs(i - x) + abs(j - y);
                    if (dist < best_dist) {
                        best_dist = dist;
                        best_i = i;
                        best_j = j;
                    }
                } else if (h[i][j] < 0 && load >= -h[i][j]) {
                    int dist = abs(i - x) + abs(j - y);
                    if (dist < best_dist) {
                        best_dist = dist;
                        best_i = i;
                        best_j = j;
                    }
                }
            }
        }

        // move one step towards the chosen cell
        if (best_i > x) {
            ans.push_back("D");
            ++x;
        } else if (best_i < x) {
            ans.push_back("U");
            --x;
        } else if (best_j > y) {
            ans.push_back("R");
            ++y;
        } else if (best_j < y) {
            ans.push_back("L");
            --y;
        } else {
            // should not happen, but break to avoid infinite loop
            break;
        }
    }

    for (const string& s : ans) {
        cout << s << '\n';
    }
    return 0;
}