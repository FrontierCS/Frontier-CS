#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    std::vector<std::vector<int>> d(n, std::vector<int>(n));
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            std::cin >> d[i][j];
        }
    }

    std::vector<std::vector<int>> f(n, std::vector<int>(n));
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            std::cin >> f[i][j];
        }
    }

    std::vector<std::pair<int, int>> facility_scores(n);
    for (int i = 0; i < n; ++i) {
        int score = 0;
        for (int j = 0; j < n; ++j) {
            score += f[i][j];
            score += f[j][i];
        }
        facility_scores[i] = {score, i};
    }

    std::vector<std::pair<int, int>> location_scores(n);
    for (int i = 0; i < n; ++i) {
        int score = 0;
        for (int j = 0; j < n; ++j) {
            score += d[i][j];
            score += d[j][i];
        }
        location_scores[i] = {score, i};
    }

    std::sort(facility_scores.rbegin(), facility_scores.rend());
    std::sort(location_scores.begin(), location_scores.end());

    std::vector<int> p(n);
    for (int i = 0; i < n; ++i) {
        p[facility_scores[i].second] = location_scores[i].second;
    }

    for (int i = 0; i < n; ++i) {
        std::cout << p[i] + 1 << (i == n - 1 ? "" : " ");
    }
    std::cout << "\n";

    return 0;
}