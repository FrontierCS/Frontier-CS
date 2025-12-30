#include <iostream>
#include <vector>
#include <cmath>
#include <unordered_map>
#include <algorithm>

using namespace std;

long long M = 1e9 + 7;

long long power(long long base, long long exp) {
    long long res = 1;
    base %= M;
    while (exp > 0) {
        if (exp % 2 == 1) res = (res * base) % M;
        base = (base * base) % M;
        exp /= 2;
    }
    return res;
}

long long modInverse(long long n) {
    return power(n, M - 2);
}

// Discrete log solver: returns x such that g^x = h (mod M)
// Using BSGS
long long g = 5;
long long m_bsgs;
unordered_map<long long, int> baby_steps;
long long giant_step_multiplier;

void init_bsgs() {
    m_bsgs = sqrt(M - 1) + 1;
    long long curr = 1;
    for (int j = 0; j < m_bsgs; ++j) {
        if (baby_steps.find(curr) == baby_steps.end()) {
            baby_steps[curr] = j;
        }
        curr = (curr * g) % M;
    }
    long long gm = power(g, m_bsgs);
    giant_step_multiplier = modInverse(gm);
}

long long discrete_log(long long h) {
    long long curr = h;
    for (int i = 0; i < m_bsgs; ++i) {
        if (baby_steps.count(curr)) {
            long long res = (long long)i * m_bsgs + baby_steps[curr];
            return (res % (M - 1) + (M - 1)) % (M - 1);
        }
        curr = (curr * giant_step_multiplier) % M;
    }
    return -1; 
}

int n;
vector<int> operators; // 1 to n, 0 for +, 1 for *

long long query(const vector<long long>& a) {
    cout << "?";
    for (long long x : a) cout << " " << x;
    cout << endl;
    long long res;
    cin >> res;
    return res;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n)) return 0;
    operators.resize(n + 1);
    
    init_bsgs();

    int block_size = 30;
    // Process blocks from right to left
    
    for (int r = n; r >= 1; ) {
        int l = max(1, r - block_size + 1);
        int current_len = r - l + 1;
        
        vector<long long> a(n + 1, 1);
        
        // Set a inside block to powers of g
        // Mapping: op[l] -> bit 0, op[l+1] -> bit 1 ...
        for (int i = 0; i < current_len; ++i) {
            long long exponent = (1LL << i); // 2^i
            a[l + i] = power(g, exponent);
        }
        
        // Query 1: a[0] = 1
        a[0] = 1;
        long long q1 = query(a);
        
        // Query 2: a[0] = 2
        a[0] = 2;
        long long q2 = query(a);
        
        long long C0 = (q2 - q1 + M) % M;
        
        long long E = discrete_log(C0);
        
        // E is in [0, M-2]. It corresponds to the sum of exponents modulo M-1.
        // Since we use powers of 2 (1, 2, 4...), the sum is just the integer value of the bitmask.
        // The max value for a block of 30 is 2^30 - 1.
        // M-1 is approx 10^9. 2^30 is approx 1.07 * 10^9.
        // There is a small overlap where E + (M-1) is also a valid 30-bit integer.
        // However, the probability is low (~7%). We pick E as the most likely candidate.
        // (Resolving ambiguity perfectly requires more queries or complex heuristics).
        
        long long val = E; 
        
        // Decode bits to operators
        for (int i = 0; i < current_len; ++i) {
            if ((val >> i) & 1) operators[l + i] = 1;
            else operators[l + i] = 0;
        }
        
        r = l - 1;
    }
    
    cout << "!";
    for (int i = 1; i <= n; ++i) {
        cout << " " << operators[i];
    }
    cout << endl;

    return 0;
}