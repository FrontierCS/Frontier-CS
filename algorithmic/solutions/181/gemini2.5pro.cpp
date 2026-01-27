#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <tuple>

void fast_io() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
}

int main() {
    fast_io();

    int n;
    std::cin >> n;

    std::vector<std::vector<int>> D(n, std::vector<int>(n));
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            std::cin >> D[i][j];
        }
    }

    std::vector<std::vector<int>> F(n, std::vector<int>(n));
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            std::cin >> F[i][j];
        }
    }

    std::vector<std::tuple<int, int, int>> facilities(n);
    std::vector<std::tuple<int, int, int>> locations(n);

    for (int i = 0; i < n; ++i) {
        int out_flow = 0, in_flow = 0;
        int out_dist = 0, in_dist = 0;
        for (int j = 0; j < n; ++j) {
            out_flow += F[i][j];
            in_flow += F[j][i];
            out_dist += D[i][j];
            in_dist += D[j][i];
        }
        facilities[i] = {out_flow, in_flow, i};
        locations[i] = {out_dist, in_dist, i};
    }

    // Sort facilities in descending order of connectivity (out-flow, in-flow).
    // Facilities with more connections should be matched with locations
    // with fewer connections.
    std::sort(facilities.rbegin(), facilities.rend());

    // Sort locations in ascending order of connectivity (out-dist, in-dist).
    std::sort(locations.begin(), locations.end());

    std::vector<int> p(n);
    for (int i = 0; i < n; ++i) {
        int facility_idx = std::get<2>(facilities[i]);
        int location_idx = std::get<2>(locations[i]);
        p[facility_idx] = location_idx + 1;
    }

    for (int i = 0; i < n; ++i) {
        std::cout << p[i] << (i == n - 1 ? "" : " ");
    }
    std::cout << "\n";

    return 0;
}