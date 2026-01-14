#include <iostream>
#include <vector>
#include <string>
#include <numeric>

void do_query(int m, const std::vector<int>& a, const std::vector<int>& b) {
    std::cout << 1 << std::endl;
    std::cout << m << std::endl;
    for (int i = 0; i < m; ++i) {
        std::cout << a[i] << (i == m - 1 ? "" : " ");
    }
    std::cout << std::endl;
    for (int i = 0; i < m; ++i) {
        std::cout << b[i] << (i == m - 1 ? "" : " ");
    }
    std::cout << std::endl;
    std::cout.flush();
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    int n;
    std::cin >> n;

    std::string s(n, '0');

    for (int k = 0; k < n; ++k) {
        // To determine S_k, we design an automaton where the state before processing S_k
        // is k, regardless of the previous bits S_0, ..., S_{k-1}.
        // We use m = k + 2 states, labeled 0 to k+1.
        // States 0, ..., k-1 form a forced path.
        // State k is the decision state.
        // States k and k+1 are sink states to hold the result.
        
        int m = k + 2;
        
        std::vector<int> a(m);
        std::vector<int> b(m);
        
        // For the first k characters (S_0 to S_{k-1}), the automaton
        // transitions from state i to i+1.
        // After S_{i-1} is processed, the state is i.
        for(int i = 0; i < k; ++i) {
            a[i] = i + 1;
            b[i] = i + 1;
        }
        
        // Before processing S_k, the state is k.
        // The transition from state k depends on S_k.
        a[k] = k;      // If S_k is '0', transition to state k.
        b[k] = k + 1;  // If S_k is '1', transition to state k+1.
        
        // States k and k+1 are sink states. Once entered, the automaton stays.
        if (k + 1 < m) {
            a[k+1] = k+1;
            b[k+1] = k+1;
        }
        
        do_query(m, a, b);
        
        int result;
        std::cin >> result;

        if (result == k) {
            s[k] = '0';
        } else {
            s[k] = '1';
        }
    }

    std::cout << 0 << std::endl;
    std::cout << s << std::endl;
    std::cout.flush();

    return 0;
}