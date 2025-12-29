#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>

// Function to print a query in the required format and flush the output.
void send_query(const std::vector<int>& positions) {
    std::cout << "? " << positions.size();
    for (int p : positions) {
        std::cout << " " << p;
    }
    std::cout << std::endl;
}

int main() {
    // Fast I/O
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    // Read problem parameters (although they are fixed for this problem)
    int R, H;
    std::cin >> R >> H;

    // A list to hold all query position sets
    std::vector<std::vector<int>> queries;

    // Stage 1: Queries to determine M_or and M_and
    // 10 queries for M_or: scout positions p where (p-1)_i = 1
    for (int i = 0; i < 10; ++i) {
        std::vector<int> positions;
        for (int p = 1; p <= 1000; ++p) {
            if (((p - 1) >> i) & 1) {
                positions.push_back(p);
            }
        }
        queries.push_back(positions);
    }

    // 10 queries for M_and: scout positions p where (p-1)_i = 0
    for (int i = 0; i < 10; ++i) {
        std::vector<int> positions;
        for (int p = 1; p <= 1000; ++p) {
            if (!(((p - 1) >> i) & 1)) {
                positions.push_back(p);
            }
        }
        queries.push_back(positions);
    }

    // Stage 2: Queries to resolve ambiguity
    // 45 queries for pairing: scout positions p where (p-1)_i XOR (p-1)_j = 1
    std::map<std::pair<int, int>, int> pair_to_idx;
    int query_idx = 20;
    for (int i = 0; i < 10; ++i) {
        for (int j = i + 1; j < 10; ++j) {
            std::vector<int> positions;
            for (int p = 1; p <= 1000; ++p) {
                if (((((p - 1) >> i) & 1) ^ (((p - 1) >> j) & 1))) {
                    positions.push_back(p);
                }
            }
            queries.push_back(positions);
            pair_to_idx[{i, j}] = query_idx++;
        }
    }

    // Send all generated queries
    for (const auto& q : queries) {
        send_query(q);
    }

    // Wait for and read the results
    std::cout << "@" << std::endl;

    int L;
    std::cin >> L;
    std::vector<int> results(L);
    for (int i = 0; i < L; ++i) {
        std::cin >> results[i];
    }

    // Process results to find the chairmen
    int m_or = 0;
    for (int i = 0; i < 10; ++i) {
        if (results[i] == 1) {
            m_or |= (1 << i);
        }
    }

    int m_and = 0;
    for (int i = 0; i < 10; ++i) {
        if (results[10 + i] == 0) {
            m_and |= (1 << i);
        }
    }

    int m_diff = m_or ^ m_and;
    int c_common = m_and;

    std::vector<int> diff_bits;
    for (int i = 0; i < 10; ++i) {
        if ((m_diff >> i) & 1) {
            diff_bits.push_back(i);
        }
    }

    int c1_mask, c2_mask;

    if (diff_bits.size() <= 1) {
        // If 0 or 1 bits differ, the pair is {c_common, m_or}
        c1_mask = c_common;
        c2_mask = m_or;
    } else {
        // If multiple bits differ, resolve ambiguity
        c1_mask = c_common;
        int s1 = diff_bits[0];
        // Assume x_{s1} = 0
        for (size_t i = 1; i < diff_bits.size(); ++i) {
            int si = diff_bits[i];
            int u = std::min(s1, si);
            int v = std::max(s1, si);
            int idx = pair_to_idx.at({u, v});
            // Result gives x_{s1} XOR x_{si} = 0 XOR x_{si} = x_{si}
            if (results[idx] == 1) {
                c1_mask |= (1 << si);
            }
        }
        c2_mask = c1_mask ^ m_diff;
    }

    int c1 = c1_mask + 1;
    int c2 = c2_mask + 1;

    // Output the final answer
    std::cout << "! " << c1 << " " << c2 << std::endl;

    return 0;
}