#include <iostream>
#include <vector>
#include <numeric>
#include <string>
#include <sstream>
#include <map>
#include <algorithm>
#include <vector>

// UDD(10, 6) found by a randomized search
const std::vector<int> UDD10_6 = {5, 50, 9, 41, 18, 12, 36, 24, 6, 33};

struct Pos {
    int i, j, k;
};

Pos to_coords(int p) {
    int val = p - 1;
    return {val / 100, (val % 100) / 10, val % 10};
}

int to_pos(const Pos& c) {
    return c.i * 100 + c.j * 10 + c.k + 1;
}

void send_query(const std::vector<int>& positions) {
    std::cout << "? " << positions.size();
    for (int p : positions) {
        std::cout << " " << p;
    }
    std::cout << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int R_in, H_in;
    std::cin >> R_in >> H_in;

    std::vector<std::vector<int>> queries(23);

    // UDD queries
    for (int p = 1; p <= 1000; ++p) {
        Pos c = to_coords(p);
        for (int bit = 0; bit < 6; ++bit) {
            if ((UDD10_6[c.i] >> bit) & 1) {
                queries[bit].push_back(p);
            }
            if ((UDD10_6[c.j] >> bit) & 1) {
                queries[6 + bit].push_back(p);
            }
            if ((UDD10_6[c.k] >> bit) & 1) {
                queries[12 + bit].push_back(p);
            }
        }
    }

    // Ambiguity-breaking queries
    int amb_coeffs[5][3] = {{1, 1, 0}, {1, 0, 1}, {0, 1, 1}, {1, 1, 1}, {1, 2, 4}};
    for (int i = 0; i < 5; ++i) {
        for (int p = 1; p <= 1000; ++p) {
            Pos c = to_coords(p);
            if ((amb_coeffs[i][0] * c.i + amb_coeffs[i][1] * c.j + amb_coeffs[i][2] * c.k) % 2 == 0) {
                queries[18 + i].push_back(p);
            }
        }
    }
    
    for (const auto& q : queries) {
        send_query(q);
    }

    std::cout << "@" << std::endl;

    int L;
    std::cin >> L;
    std::vector<int> results(L);
    for (int i = 0; i < L; ++i) {
        std::cin >> results[i];
    }
    
    int bi = 0, bj = 0, bk = 0;
    for (int i = 0; i < 6; ++i) {
        if (results[i]) bi |= (1 << i);
        if (results[6 + i]) bj |= (1 << i);
        if (results[12 + i]) bk |= (1 << i);
    }
    
    std::vector<int> amb_res;
    for (int i = 0; i < 5; ++i) {
        amb_res.push_back(results[18 + i]);
    }

    std::map<int, std::pair<int, int>> or_map;
    for (int i = 0; i < 10; ++i) {
        for (int j = i; j < 10; ++j) {
            or_map[UDD10_6[i] | UDD10_6[j]] = {i, j};
        }
    }

    int i1 = or_map[bi].first, i2 = or_map[bi].second;
    int j1 = or_map[bj].first, j2 = or_map[bj].second;
    int k1 = or_map[bk].first, k2 = or_map[bk].second;

    std::vector<std::pair<int, int>> candidates;
    
    Pos c1_cand, c2_cand;
    c1_cand = {i1, j1, k1}; c2_cand = {i2, j2, k2};
    candidates.push_back({to_pos(c1_cand), to_pos(c2_cand)});

    c1_cand = {i1, j1, k2}; c2_cand = {i2, j2, k1};
    candidates.push_back({to_pos(c1_cand), to_pos(c2_cand)});
    
    c1_cand = {i1, j2, k1}; c2_cand = {i2, j1, k2};
    candidates.push_back({to_pos(c1_cand), to_pos(c2_cand)});

    c1_cand = {i1, j2, k2}; c2_cand = {i2, j1, k1};
    candidates.push_back({to_pos(c1_cand), to_pos(c2_cand)});

    for(auto& p : candidates) {
        if (p.first > p.second) std::swap(p.first, p.second);
    }
    std::sort(candidates.begin(), candidates.end());
    candidates.erase(std::unique(candidates.begin(), candidates.end()), candidates.end());


    for (const auto& cand : candidates) {
        int p1 = cand.first;
        int p2 = cand.second;
        bool match = true;
        for (int i = 0; i < 5; ++i) {
            Pos c1 = to_coords(p1);
            Pos c2 = to_coords(p2);
            int pred_res = 0;
            if ((amb_coeffs[i][0] * c1.i + amb_coeffs[i][1] * c1.j + amb_coeffs[i][2] * c1.k) % 2 == 0) {
                pred_res = 1;
            }
            if ((amb_coeffs[i][0] * c2.i + amb_coeffs[i][1] * c2.j + amb_coeffs[i][2] * c2.k) % 2 == 0) {
                pred_res = 1;
            }
            if (pred_res != amb_res[i]) {
                match = false;
                break;
            }
        }
        if (match) {
            std::cout << "! " << p1 << " " << p2 << std::endl;
            return 0;
        }
    }
    
    // Should not be reached with a robust set of ambiguity-breaking queries.
    // In case of an unforeseen collision, we output a default guess.
    std::cout << "! 1 1" << std::endl;

    return 0;
}