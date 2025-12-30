#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>
#include <functional>

void send_query(const std::vector<int>& positions) {
    std::cout << "? " << positions.size();
    for (int p : positions) {
        std::cout << " " << p;
    }
    std::cout << std::endl;
}

int base6_digit(int n, int i) {
    for (int k = 0; k < i; ++k) {
        n /= 6;
    }
    return n % 6;
}

std::vector<int> candidates;
std::vector<std::vector<int>> digit_sets;
std::vector<int> current_digits(4);

void generate_candidates_recursive(int k) {
    if (k == 4) {
        int val = 0;
        int p6 = 1;
        for (int i = 0; i < 4; ++i) {
            val += current_digits[i] * p6;
            p6 *= 6;
        }
        if (val < 1000) {
            candidates.push_back(val + 1);
        }
        return;
    }
    for (int digit : digit_sets[k]) {
        current_digits[k] = digit;
        generate_candidates_recursive(k + 1);
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int R, H;
    std::cin >> R >> H;

    // Queries for base-6 digits
    for (int i = 0; i < 4; ++i) {
        for (int d = 0; d < 6; ++d) {
            std::vector<int> positions;
            for (int k = 1; k <= 1000; ++k) {
                if (base6_digit(k - 1, i) == d) {
                    positions.push_back(k);
                }
            }
            send_query(positions);
        }
    }

    // Queries for bits
    for (int i = 0; i < 10; ++i) {
        std::vector<int> positions;
        for (int k = 1; k <= 1000; ++k) {
            if (((k - 1) >> i) & 1) {
                positions.push_back(k);
            }
        }
        send_query(positions);
    }
    
    std::cout << "@" << std::endl;

    int L;
    std::cin >> L;
    std::vector<int> results(L);
    for (int i = 0; i < L; ++i) {
        std::cin >> results[i];
    }

    digit_sets.resize(4);
    for (int i = 0; i < 4; ++i) {
        for (int d = 0; d < 6; ++d) {
            if (results[i * 6 + d] == 1) {
                digit_sets[i].push_back(d);
            }
        }
    }

    int or_val = 0;
    for (int i = 0; i < 10; ++i) {
        if (results[24 + i] == 1) {
            or_val |= (1 << i);
        }
    }
    
    generate_candidates_recursive(0);
    
    std::vector<int> final_candidates;
    for (int p : candidates) {
        if (((p - 1) | or_val) == or_val) {
            final_candidates.push_back(p);
        }
    }

    if (final_candidates.size() == 1) {
        std::cout << "! " << final_candidates[0] << " " << final_candidates[0] << std::endl;
    } else {
        for (size_t i = 0; i < final_candidates.size(); ++i) {
            for (size_t j = i; j < final_candidates.size(); ++j) {
                if (((final_candidates[i] - 1) | (final_candidates[j] - 1)) == or_val) {
                    std::cout << "! " << final_candidates[i] << " " << final_candidates[j] << std::endl;
                    return 0;
                }
            }
        }
    }

    return 0;
}