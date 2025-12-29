#include <iostream>
#include <vector>
#include <numeric>
#include <random>
#include <chrono>
#include <bitset>

const int NUM_POSITIONS = 1000;
const int NUM_ROBOTS = 75;

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int R, H;
    std::cin >> R >> H;

    std::mt19937 rng(std::chrono::steady_clock::now().time_since_epoch().count());
    std::uniform_int_distribution<int> dist(0, 1);

    std::vector<std::bitset<NUM_POSITIONS + 1>> S_T(NUM_ROBOTS);
    for (int r = 0; r < NUM_ROBOTS; ++r) {
        for (int p = 1; p <= NUM_POSITIONS; ++p) {
            if (dist(rng)) {
                S_T[r].set(p);
            }
        }
    }

    for (int r = 0; r < NUM_ROBOTS; ++r) {
        std::vector<int> current_query;
        for (int p = 1; p <= NUM_POSITIONS; ++p) {
            if (S_T[r].test(p)) {
                current_query.push_back(p);
            }
        }
        std::cout << "? " << current_query.size();
        for (int pos : current_query) {
            std::cout << " " << pos;
        }
        std::cout << std::endl;
    }

    std::cout << "@" << std::endl;

    int L;
    std::cin >> L;
    std::vector<int> A(L);
    for (int i = 0; i < L; ++i) {
        std::cin >> A[i];
    }

    for (int c1 = 1; c1 <= NUM_POSITIONS; ++c1) {
        for (int c2 = c1; c2 <= NUM_POSITIONS; ++c2) {
            bool match = true;
            for (int r = 0; r < L; ++r) {
                bool robot_sees_chair = S_T[r].test(c1) || S_T[r].test(c2);
                if (robot_sees_chair != (A[r] == 1)) {
                    match = false;
                    break;
                }
            }
            if (match) {
                std::cout << "! " << c1 << " " << c2 << std::endl;
                return 0;
            }
        }
    }

    return 0;
}