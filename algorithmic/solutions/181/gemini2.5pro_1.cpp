#include <iostream>
#include <vector>
#include <algorithm>
#include <utility>

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

    // Calculate total degrees (in-degree + out-degree) for facilities
    std::vector<int> facility_row_sum(n, 0);
    std::vector<int> facility_col_sum(n, 0);
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            facility_row_sum[i] += f[i][j];
            facility_col_sum[j] += f[i][j];
        }
    }

    std::vector<std::pair<int, int>> facility_degrees(n);
    for (int i = 0; i < n; ++i) {
        facility_degrees[i] = {facility_row_sum[i] + facility_col_sum[i], i};
    }

    // Calculate total degrees (in-degree + out-degree) for locations
    std::vector<int> location_row_sum(n, 0);
    std::vector<int> location_col_sum(n, 0);
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            location_row_sum[i] += d[i][j];
            location_col_sum[j] += d[i][j];
        }
    }

    std::vector<std::pair<int, int>> location_degrees(n);
    for (int i = 0; i < n; ++i) {
        location_degrees[i] = {location_row_sum[i] + location_col_sum[i], i};
    }

    // Sort facilities by degree in descending order
    std::sort(facility_degrees.rbegin(), facility_degrees.rend());
    
    // Sort locations by degree in ascending order
    std::sort(location_degrees.begin(), location_degrees.end());

    // Create the permutation by mapping high-flow facilities to low-distance locations
    std::vector<int> p(n);
    for (int i = 0; i < n; ++i) {
        int facility_idx = facility_degrees[i].second;
        int location_idx = location_degrees[i].second;
        p[facility_idx] = location_idx;
    }

    // Output the resulting permutation (1-based)
    for (int i = 0; i < n; ++i) {
        std::cout << p[i] + 1 << (i == n - 1 ? "" : " ");
    }
    std::cout << std::endl;

    return 0;
}