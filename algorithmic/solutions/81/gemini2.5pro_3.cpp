#include <iostream>
#include <vector>
#include <string>
#include <numeric>

void do_query(int m, const std::vector<int>& a, const std::vector<int>& b) {
    std::cout << "1 " << m << std::endl;
    for (int i = 0; i < m; ++i) {
        std::cout << a[i] << (i == m - 1 ? "" : " ");
    }
    std::cout << std::endl;
    for (int i = 0; i < m; ++i) {
        std::cout << b[i] << (i == m - 1 ? "" : " ");
    }
    std::cout << std::endl;
}

void do_guess(const std::string& s) {
    std::cout << "0 " << s << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int N;
    std::cin >> N;

    const int B = 5;
    const int C = 40;
    const int M = 102;

    std::string s_found = "";
    int popc = 0;
    int num_blocks = N / B;

    for (int q = 0; q < num_blocks; ++q) {
        int p_q = popc % C;

        std::vector<int> a(M), b(M);
        // Default transitions: self-loops
        for(int i = 0; i < M; ++i) {
            a[i] = i;
            b[i] = i;
        }

        // Path-finding transitions
        for (int i = 0; i < C; ++i) {
            a[i] = i;
            b[i] = (i + 1) % C;
        }

        // Tree transitions
        // Root's children
        a[p_q] = C;
        b[p_q] = C + 1;

        // Internal nodes
        int current_level_start = C;
        for (int d = 0; d < B - 1; ++d) {
            int num_nodes_in_level = 1 << (d + 1);
            int next_level_start = current_level_start + num_nodes_in_level;
            for (int i = 0; i < num_nodes_in_level; ++i) {
                int u = current_level_start + i;
                a[u] = next_level_start + 2 * i;
                b[u] = next_level_start + 2 * i + 1;
            }
            current_level_start = next_level_start;
        }
        int leaf_start_state = current_level_start;
        
        do_query(M, a, b);
        std::cout.flush();

        int result;
        std::cin >> result;
        
        int val = result - leaf_start_state;
        
        std::string block_s = "";
        int block_popc = 0;
        for (int i = B - 1; i >= 0; --i) {
            if ((val >> i) & 1) {
                block_s += '1';
                block_popc++;
            } else {
                block_s += '0';
            }
        }
        s_found += block_s;
        popc += block_popc;
    }

    do_guess(s_found);
    std::cout.flush();

    return 0;
}