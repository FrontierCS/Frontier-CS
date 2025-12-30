#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    int n;
    std::cin >> n;

    std::string s(n, ' ');
    int p_open = -1;

    // Stage 1: Find an index with an opening bracket.
    // We can systematically check pairs (i, j) with i < j.
    // The first pair (i, j) that gives f(s_i s_j) = 1 must have s_i = '(' and s_j = ')'.
    for (int i = 1; i <= n; ++i) {
        for (int j = i + 1; j <= n; ++j) {
            std::cout << "0 2 " << i << " " << j << std::endl;
            int res;
            std::cin >> res;
            if (res == 1) {
                p_open = i;
                s[i - 1] = '(';
                s[j - 1] = ')';
                goto found_open_bracket;
            }
        }
    }
    
found_open_bracket:
    // If p_open is still -1, it implies a special structure, e.g., )))...))((...((
    // The first opening bracket must be at some index i, and all preceding are ')'
    // and all succeeding j until the first ')' give f(i, j) = 0.
    // The systematic search above is guaranteed to find such a pair since at least one '(' and one ')' exist.
    
    // Stage 2: Determine remaining characters using the anchor p_open.
    for (int i = 1; i <= n; ++i) {
        if (s[i - 1] != ' ') {
            continue;
        }
        std::cout << "0 2 " << p_open << " " << i << std::endl;
        int res;
        std::cin >> res;
        if (res == 1) {
            s[i - 1] = ')';
        } else {
            s[i - 1] = '(';
        }
    }

    std::cout << "1 " << s << std::endl;

    return 0;
}