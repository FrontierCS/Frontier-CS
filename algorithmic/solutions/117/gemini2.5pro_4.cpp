#include <iostream>
#include <vector>
#include <cmath>
#include <iomanip>
#include <numeric>
#include <algorithm>
#include <map>
#include <stdexcept>

using namespace std;

using ld = long double;

int N;
const ld L_COORD = -1e12;
const ld R_COORD = 1e12;
const ld EPS = 1e-9;

ld query(ld x, ld y) {
    if (abs(x) > R_COORD || abs(y) > R_COORD) {
        throw runtime_error("Coordinates out of bounds");
    }

    cout << "? " << fixed << setprecision(10) << x << " " << y << endl;
    ld response;
    cin >> response;
    return response;
}

// =================== Logic for non-horizontal lines ===================

map<long long, vector<ld>> found_jumps_x;

ld get_dx(ld x_val, ld y_val) {
    ld s1 = query(x_val - EPS, y_val);
    ld s2 = query(x_val + EPS, y_val);
    return (s2 - s1) / (2.0L * EPS);
}

void find_jumps_x_recursive(ld y_val, ld L, ld R, ld dL, ld dR) {
    if (abs(dL - dR) < 1e-7) {
        return;
    }

    if (R - L < 1e-6) {
        ld jump_size = abs(dR - dL);
        ld J = jump_size;
        ld J2 = J * J;
        
        if (J < 1e-7) return;
        
        ld delta = J2 * J2 + 16.0L * J2;
        if (delta < 0) return;
        ld A = (J2 + sqrt(delta)) / 8.0L;
        
        long long abs_a_sq_rounded = round(A);
        if (abs_a_sq_rounded == 0) return;
        long long abs_a_rounded = round(sqrt(A));
        
        if (abs(abs_a_sq_rounded - A) > 1e-4 || abs_a_rounded * abs_a_rounded != abs_a_sq_rounded) {
             return;
        }
        found_jumps_x[abs_a_rounded].push_back((L+R)/2.0L);
        return;
    }

    ld M = L + (R - L) / 2.0L;
    ld dM = get_dx(M, y_val);

    find_jumps_x_recursive(y_val, L, M, dL, dM);
    find_jumps_x_recursive(y_val, M, R, dM, dR);
}

// =================== Logic for horizontal lines ===================

vector<long long> found_b_for_horizontal;
vector<pair<long long, long long>> non_horizontal_lines;

ld get_dy_rem(ld y_val) {
    ld s1 = query(0, y_val - EPS);
    ld s2 = query(0, y_val + EPS);
    ld dy_total = (s2 - s1) / (2.0L * EPS);

    ld dy_known = 0;
    for(const auto& line : non_horizontal_lines) {
        ld a = line.first;
        ld b = line.second;
        ld val = y_val - b;
        int sign = (val > EPS) - (val < -EPS);
        if (abs(a*a + 1.0L) > 1e-12)
            dy_known += sign / sqrt(a*a + 1.0L);
    }
    return dy_total - dy_known;
}

void find_jumps_y_recursive(long long L, long long R) {
    ld dL = get_dy_rem(L - 0.5L);
    ld dR = get_dy_rem(R + 0.5L);

    if (abs(dL - dR) < 1e-7) {
        return;
    }

    if (L == R) {
        if (abs(abs(dR - dL) - 2.0L) < 1e-4) {
            found_b_for_horizontal.push_back(L);
        }
        return;
    }

    long long M = L + (R - L) / 2;
    find_jumps_y_recursive(L, M);
    find_jumps_y_recursive(M + 1, R);
}


int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> N;

    vector<long long> a_s, b_s;

    {
        ld x_min = -10001.0;
        ld x_max = 10001.0;
        
        found_jumps_x.clear();
        find_jumps_x_recursive(0, x_min, x_max, get_dx(x_min, 0), get_dx(x_max, 0));
        map<long long, vector<ld>> intercepts0 = found_jumps_x;

        found_jumps_x.clear();
        find_jumps_x_recursive(1, x_min, x_max, get_dx(x_min, 1), get_dx(x_max, 1));
        map<long long, vector<ld>> intercepts1 = found_jumps_x;
        
        for(auto const& [abs_a, x0_list_const] : intercepts0) {
            if (abs_a == 0 || intercepts1.find(abs_a) == intercepts1.end()) {
                continue;
            }
            vector<ld> x0_list = x0_list_const;
            vector<ld> x1_list = intercepts1[abs_a];
            sort(x0_list.begin(), x0_list.end());
            sort(x1_list.begin(), x1_list.end());
            
            vector<bool> used(x1_list.size(), false);
            for(ld x0 : x0_list) {
                for(size_t i = 0; i < x1_list.size(); ++i) {
                    if(used[i]) continue;
                    ld x1 = x1_list[i];
                    
                    ld diff = x1 - x0;
                    if (abs(diff) < 1e-7) continue;

                    if (abs(abs(diff) * abs_a - 1.0L) < 1e-4) {
                        ld a_cand = 1.0L / diff;
                        ld b_cand = -a_cand * x0;
                        
                        long long a_res = round(a_cand);
                        long long b_res = round(b_cand);

                        if (abs(a_cand - a_res) < 1e-4 && abs(b_cand - b_res) < 1e-4) {
                           non_horizontal_lines.push_back({a_res, b_res});
                           used[i] = true;
                           break;
                        }
                    }
                }
            }
        }
    }

    for(const auto& line : non_horizontal_lines) {
        a_s.push_back(line.first);
        b_s.push_back(line.second);
    }

    if (a_s.size() < N) {
        long long y_min = -10000;
        long long y_max = 10000;
        find_jumps_y_recursive(y_min, y_max);

        for(long long b_val : found_b_for_horizontal) {
            a_s.push_back(0);
            b_s.push_back(b_val);
        }
    }

    cout << "!";
    for (int i = 0; i < N; ++i) cout << " " << a_s[i];
    for (int i = 0; i < N; ++i) cout << " " << b_s[i];
    cout << endl;

    return 0;
}