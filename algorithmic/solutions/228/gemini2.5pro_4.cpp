#include <iostream>
#include <string>
#include <vector>
#include <cmath>

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    
    std::string s;
    std::cin >> s;
    int n = s.length();

    std::vector<int> po(n + 1, 0);
    for (int i = 0; i < n; ++i) {
        po[i + 1] = po[i] + (s[i] - '0');
    }

    long long ans = 0;
    
    for (int j = 0; j < n; ++j) {
        for (int o = 1; ; ++o) {
            long long len = (long long)o * o + o;
            if (j + 1 < len) {
                break;
            }
            int i = j + 1 - len;
            if (po[j + 1] - po[i] == o) {
                ans++;
            }
        }
    }
    
    std::cout << ans << std::endl;
    
    return 0;
}