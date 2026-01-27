#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

// This function calculates the ranks of original items based on a sorted list of pairs.
// The rank is simply the position in the sorted list.
// Input: sorted_pairs - a vector of pairs {value, original_index}, sorted by value.
// Output: ranks - a vector where ranks[original_index] = rank.
void get_ranks(const std::vector<std::pair<int, int>>& sorted_pairs, std::vector<int>& ranks) {
    for (size_t i = 0; i < sorted_pairs.size(); ++i) {
        ranks[sorted_pairs[i].second] = i;
    }
}

void solve() {
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

    // Calculate in-degrees and out-degrees for both facilities (F) and locations (D).
    std::vector<std::pair<int, int>> out_f(n), in_f(n);
    std::vector<std::pair<int, int>> out_d(n), in_d(n);
    for (int i = 0; i < n; ++i) {
        int out_f_deg = 0, in_f_deg = 0;
        int out_d_deg = 0, in_d_deg = 0;
        for (int j = 0; j < n; ++j) {
            out_f_deg += f[i][j];
            in_f_deg += f[j][i];
            out_d_deg += d[i][j];
            in_d_deg += d[j][i];
        }
        out_f[i] = {out_f_deg, i};
        in_f[i] = {in_f_deg, i};
        out_d[i] = {out_d_deg, i};
        in_d[i] = {in_d_deg, i};
    }
    
    // Sort facilities by degrees, descending, to prioritize high-degree ones.
    std::sort(out_f.rbegin(), out_f.rend());
    std::sort(in_f.rbegin(), in_f.rend());

    // Sort locations by degrees, ascending, to prioritize low-degree ones.
    std::sort(out_d.begin(), out_d.end());
    std::sort(in_d.begin(), in_d.end());

    // Get ranks based on the sorted lists. A lower rank (index in sorted list) is "better".
    std::vector<int> rank_out_f(n), rank_in_f(n);
    std::vector<int> rank_out_d(n), rank_in_d(n);
    get_ranks(out_f, rank_out_f);
    get_ranks(in_f, rank_in_f);
    get_ranks(out_d, rank_out_d);
    get_ranks(in_d, rank_in_d);

    // Combine ranks to get a total score for each facility and location.
    // A lower score indicates a more "critical" item.
    std::vector<std::pair<int, int>> facility_scores(n);
    for (int i = 0; i < n; ++i) {
        facility_scores[i] = {rank_out_f[i] + rank_in_f[i], i};
    }
    std::vector<std::pair<int, int>> location_scores(n);
    for (int i = 0; i < n; ++i) {
        location_scores[i] = {rank_out_d[i] + rank_in_d[i], i};
    }

    // Sort facilities and locations by their combined scores in ascending order.
    std::sort(facility_scores.begin(), facility_scores.end());
    std::sort(location_scores.begin(), location_scores.end());

    // Construct the permutation by matching items with the same score rank.
    std::vector<int> p(n);
    for (int i = 0; i < n; ++i) {
        int facility_idx = facility_scores[i].second;
        int location_idx = location_scores[i].second;
        p[facility_idx] = location_idx;
    }

    // Output the resulting permutation, converting to 1-based indexing.
    for (int i = 0; i < n; ++i) {
        std::cout << p[i] + 1 << (i == n - 1 ? "" : " ");
    }
    std::cout << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    solve();
    return 0;
}