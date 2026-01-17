#include <iostream>
#include <vector>
#include <string>
#include <numeric>

void query_and_print(int m, const std::vector<int>& a, const std::vector<int>& b) {
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
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    int n;
    std::cin >> n;

    std::string s(n, '0');

    for (int i = 0; i < n; ++i) {
        int m = i + 3;
        std::vector<int> a(m);
        std::vector<int> b(m);

        // Default to self-loops, useful for states not explicitly set
        for(int j=0; j<m; ++j) {
            a[j] = j;
            b[j] = j;
        }

        // Chain to state i
        for (int j = 0; j < i; ++j) {
            a[j] = j + 1;
            b[j] = j + 1;
        }

        // Branch on S_i
        a[i] = i + 1;
        b[i] = i + 2;

        // Sink states
        a[i + 1] = i + 1;
        b[i + 1] = i + 1;
        a[i + 2] = i + 2;
        b[i + 2] = i + 2;
        
        query_and_print(m, a, b);

        int result;
        std::cin >> result;

        if (result == i + 1) {
            s[i] = '0';
        } else {
            s[i] = '1';
        }
    }

    std::cout << 0 << std::endl;
    std::cout << s << std::endl;

    return 0;
}