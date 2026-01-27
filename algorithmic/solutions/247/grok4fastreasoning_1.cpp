#include <bits/stdc++.h>

using namespace std;

int main() {
    int N;
    cin >> N;
    vector<int> A(N);
    long long sumA = 0;
    for (int &x : A) {
        cin >> x;
        sumA += x;
    }
    vector<int> B(N);
    long long sumB = 0;
    for (int &x : B) {
        cin >> x;
        sumB += x;
    }
    if (sumA != sumB) {
        cout << "No" << endl;
        return 0;
    }
    vector<int> current = A;
    vector<pair<int, int>> ops;
    auto l1_dist = [&](const vector<int>& arr) -> int {
        int s = 0;
        for (int i = 0; i < N; i++) s += abs(arr[i] - B[i]);
        return s;
    };
    int max_steps = 100000;
    while (l1_dist(current) > 0 && (int)ops.size() < max_steps) {
        int best_red = -1;
        pair<int, int> best_pair = {-1, -1};
        int best_abs_delta = INT_MAX;
        int best_i = -1;
        for (int i = 0; i < N; i++) {
            for (int j = i + 1; j < N; j++) {
                int x = current[i], y = current[j];
                int delta = y - x - 1;
                int nx = y - 1;
                int ny = x + 1;
                int old_l = abs(current[i] - B[i]) + abs(current[j] - B[j]);
                int new_l = abs(nx - B[i]) + abs(ny - B[j]);
                int red = old_l - new_l;
                bool better = (red > best_red) ||
                              (red == best_red && abs(delta) < best_abs_delta) ||
                              (red == best_red && abs(delta) == best_abs_delta && i > best_i);
                if (better) {
                    best_red = red;
                    best_pair = {i, j};
                    best_abs_delta = abs(delta);
                    best_i = i;
                }
            }
        }
        if (best_red <= 0) break;
        int i = best_pair.first, j = best_pair.second;
        int x = current[i], y = current[j];
        current[i] = y - 1;
        current[j] = x + 1;
        ops.emplace_back(i + 1, j + 1);
    }
    if (l1_dist(current) == 0) {
        cout << "Yes" << endl;
        cout << ops.size() << endl;
        for (auto p : ops) {
            cout << p.first << " " << p.second << endl;
        }
    } else {
        cout << "No" << endl;
    }
    return 0;
}