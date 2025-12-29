#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>

struct Company {
    int x, y;
    long long r;
};

struct Result {
    int a, b, c, d;
};

std::vector<Company> companies;
std::vector<Result> results;
std::vector<int> p_indices_buffer;

void solve(int xs, int ys, int xe, int ye, int p_start, int p_end) {
    if (p_end - p_start == 1) {
        int company_idx = p_indices_buffer[p_start];
        results[company_idx] = {xs, ys, xe, ye};
        return;
    }

    bool is_vert_split_preferred = (xe - xs) >= (ye - ys);
    
    auto attempt_split = [&](bool vertical_split) -> bool {
        if (vertical_split) {
            std::sort(p_indices_buffer.begin() + p_start, p_indices_buffer.begin() + p_end, [&](int i, int j){
                return companies[i].x < companies[j].x;
            });
        } else {
            std::sort(p_indices_buffer.begin() + p_start, p_indices_buffer.begin() + p_end, [&](int i, int j){
                return companies[i].y < companies[j].y;
            });
        }
        
        long long total_r = 0;
        for (int i = p_start; i < p_end; ++i) {
            total_r += companies[p_indices_buffer[i]].r;
        }
        
        int best_m_offset = -1;
        int best_c = -1;
        long double min_err = 1e18;

        long long current_r_sum = 0;
        for (int m_offset = 0; m_offset < (p_end - p_start - 1); ++m_offset) {
            int current_p_idx = p_start + m_offset;
            current_r_sum += companies[p_indices_buffer[current_p_idx]].r;

            int company_idx1 = p_indices_buffer[current_p_idx];
            int company_idx2 = p_indices_buffer[current_p_idx + 1];

            int coord1 = vertical_split ? companies[company_idx1].x : companies[company_idx1].y;
            int coord2 = vertical_split ? companies[company_idx2].x : companies[company_idx2].y;
            
            if (coord1 >= coord2) continue;

            int start_coord = vertical_split ? xs : ys;
            int end_coord = vertical_split ? xe : ye;
            
            long double ideal_c_double = (long double)start_coord + (long double)(end_coord - start_coord) * current_r_sum / total_r;
            
            int c = round(ideal_c_double);
            
            int c_min = coord1 + 1;
            int c_max = coord2;

            c = std::max(c_min, std::min(c_max, c));

            long double err = std::abs(c - ideal_c_double);
            
            if (err < min_err) {
                min_err = err;
                best_m_offset = m_offset;
                best_c = c;
            }
        }
        
        if (best_m_offset == -1) return false;

        int split_point_idx = p_start + best_m_offset + 1;

        if (vertical_split) {
            solve(xs, ys, best_c, ye, p_start, split_point_idx);
            solve(best_c, ys, xe, ye, split_point_idx, p_end);
        } else {
            solve(xs, ys, xe, best_c, p_start, split_point_idx);
            solve(xs, best_c, xe, ye, split_point_idx, p_end);
        }
        return true;
    };

    if (!attempt_split(is_vert_split_preferred)) {
        attempt_split(!is_vert_split_preferred);
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;
    companies.resize(n);
    results.resize(n);
    p_indices_buffer.resize(n);
    
    for (int i = 0; i < n; ++i) {
        std::cin >> companies[i].x >> companies[i].y >> companies[i].r;
        p_indices_buffer[i] = i;
    }

    solve(0, 0, 10000, 10000, 0, n);

    for (int i = 0; i < n; ++i) {
        std::cout << results[i].a << " " << results[i].b << " " << results[i].c << " " << results[i].d << "\n";
    }

    return 0;
}