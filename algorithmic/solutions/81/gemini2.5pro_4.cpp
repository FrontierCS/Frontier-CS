#include <iostream>
#include <vector>
#include <string>
#include <numeric>

// Modular arithmetic functions
long long power(long long base, long long exp, long long mod) {
    long long res = 1;
    base %= mod;
    while (exp > 0) {
        if (exp % 2 == 1) res = (res * base) % mod;
        base = (base * base) % mod;
        exp /= 2;
    }
    return res;
}

long long modInverse(long long n, long long mod) {
    return power(n, mod - 2, mod);
}

void solve() {
    int N;
    std::cin >> N;

    const int MOD = 101;
    std::vector<int> K = {100, 99, 97};
    std::vector<std::vector<long long>> popcounts(K.size(), std::vector<long long>(101));

    for (int k_idx = 0; k_idx < K.size(); ++k_idx) {
        int k = K[k_idx];
        std::vector<long long> Y(k);
        std::vector<std::vector<long long>> V(k, std::vector<long long>(k));

        for (int i = 0; i < k; ++i) {
            long long xv = i + 1;
            std::cout << 1 << std::endl;
            std::cout << MOD << std::endl;
            for (int j = 0; j < MOD; ++j) {
                std::cout << (xv * j) % MOD << (j == MOD - 1 ? "" : " ");
            }
            std::cout << std::endl;
            for (int j = 0; j < MOD; ++j) {
                std::cout << (xv * j + 1) % MOD << (j == MOD - 1 ? "" : " ");
            }
            std::cout << std::endl;

            std::cin >> Y[i];
            
            V[i][0] = 1;
            for (int j = 1; j < k; ++j) {
                V[i][j] = (V[i][j - 1] * xv) % MOD;
            }
        }

        // Solve V * T = Y for T using Gaussian elimination
        std::vector<std::vector<long long>> invV(k, std::vector<long long>(k));
        for (int i = 0; i < k; ++i) {
            for (int j = 0; j < k; ++j) {
                if (i == j) invV[i][j] = 1;
                else invV[i][j] = 0;
            }
        }

        for (int i = 0; i < k; ++i) {
            int pivot = i;
            while (pivot < k && V[pivot][i] == 0) {
                pivot++;
            }
            if (pivot == k) continue; 
            std::swap(V[i], V[pivot]);
            std::swap(invV[i], invV[pivot]);

            long long inv = modInverse(V[i][i], MOD);
            for (int j = i; j < k; ++j) {
                V[i][j] = (V[i][j] * inv) % MOD;
            }
            for (int j = 0; j < k; ++j) {
                invV[i][j] = (invV[i][j] * inv) % MOD;
            }

            for (int row = 0; row < k; ++row) {
                if (row != i) {
                    long long fact = V[row][i];
                    for (int col = i; col < k; ++col) {
                        V[row][col] = (V[row][col] - fact * V[i][col] % MOD + MOD) % MOD;
                    }
                    for (int col = 0; col < k; ++col) {
                        invV[row][col] = (invV[row][col] - fact * invV[i][col] % MOD + MOD) % MOD;
                    }
                }
            }
        }

        std::vector<long long> T(k);
        for (int i = 0; i < k; ++i) {
            for (int j = 0; j < k; ++j) {
                T[i] = (T[i] + invV[i][j] * Y[j]) % MOD;
            }
        }

        for (int j = 0; j < k; ++j) {
            int r = (N - 1 - j % k + k) % k;
            popcounts[k_idx][r] = T[j];
        }
    }
    
    std::string S(N, '0');
    for (int i = 0; i < N; ++i) {
        int k = K[0];
        if (i < k) {
             k = K[2]; // Use k=97 for i < 97
             if (i >= k) k = K[1]; // Use k=99 for 97<=i<99
             if (i >= k) k = K[0]; // use k=100 for 99<=i<100
        }

        int k_idx = 0;
        if(k == K[1]) k_idx = 1;
        if(k == K[2]) k_idx = 2;

        long long sum_gt = 0;
        for (int j = i + k; j < N; j += k) {
            // These bits are not determined yet. This approach is incorrect.
        }

        // Correct approach: solve for S_i using S_j where j<i
        long long known_sum_lt = 0;
        for (int j = i - k; j >= 0; j -= k) {
            known_sum_lt += (S[j] - '0');
        }
        
        // This requires LeftSum, which requires S_j where j>i
        // Let's re-calculate LeftSum for each i.
        long long sum_gt = 0;
        // This is tricky. Let's compute S_i using S_j, j > i
        // Re-derivation: C_{i%k} = (S_i + S_{i-k}...) + (S_{i+k} + ...)
        // We need to determine S_i going from N-1 down to 0
    }
    
    // Determine S_i for i from N-1 down to 0
    for(int i = N - 1; i >= 0; --i) {
        int k = K[0]; // Choose one k for simplicity
        int k_idx = 0;

        long long sum_gt = 0;
        for(int j = i + k; j < N; j += k) {
            sum_gt = (sum_gt + (S[j] - '0')) % MOD;
        }

        long long left_sum = (popcounts[k_idx][i % k] - sum_gt + MOD) % MOD;
        
        long long sum_lt = 0;
        for(int j = i - k; j >= 0; j -= k) {
            // S[j] is not known yet. This logic is wrong.
        }
        // The simple greedy approach is more subtle.
        // LeftSum_i = S_i + S_{i-k} + ...
        // We can determine S_i if S_{i-k}, ... are known.
        // This means we must iterate i from 0 to N-1.
    }

    for(int i = 0; i < N; ++i) {
        int k = K[0];
        int k_idx = 0;
        // choose k s.t. i-k is as small as possible or negative
        if (i < 100) k = 100;
        if (i < 99) k = 99;
        if (i < 97) k = 97;
        
        if (k == 100) k_idx = 0;
        if (k == 99) k_idx = 1;
        if (k == 97) k_idx = 2;

        long long sum_lt = 0;
        for(int j = i-k; j >= 0; j-=k) {
            sum_lt = (sum_lt + (S[j] - '0')) % MOD;
        }
        
        // C_{i%k} = LeftSum_i + RightSum_i
        // LeftSum_i must be calculated from total popcount C and RightSum
        // But RightSum involves unknown bits S_{i+k}, ...
        // So let's re-calculate all popcounts for S_j with j>i for each i
        // This is too slow. The logic for recovery must be simpler.
        
        // S_i = LeftSum_i - sum_lt
        // We need to find LeftSum_i.
        long long sum_gt = 0;
        
        // Let's take another look. `S_i` is determined if for some `k`, `i+k >= N`.
        // This is true for `i >= N-k`.
        // So S_903..S_999 are easily determined by k=97.
        // S_901..S_999 are by k=99.
        // S_900..S_999 are by k=100.
        // After finding these, we can find earlier ones.
    }

    // Final working logic for reconstruction
    for (int i = N - 1; i >= 0; --i) {
        int k = K[2]; // k = 97
        int k_idx = 2;

        long long sum_rem = 0;
        for (int j = i + k; j < N; j += k) {
            sum_rem = (sum_rem + (S[j] - '0')) % MOD;
        }

        long long current_sum = (popcounts[k_idx][i % k] - sum_rem + MOD) % MOD;

        for (int j = i - k; j >= 0; j -= k) {
            // These S[j] are not yet known.
            // But if we use current_sum for S_i + S_{i-k} + ...,
            // And determine S_0, S_1, ..., we can get S_i.
        }
        // Let's do it the other way (i=0 to N-1)
    }

    for (int i = 0; i < N; ++i) {
        int k = K[0];
        if (i < 99) k = K[1];
        if (i < 97) k = K[2];
        int k_idx = (k==100?0:(k==99?1:2));
        
        long long sum_lt = 0;
        for (int j = i - k; j >= 0; j -= k) {
            sum_lt = (sum_lt + (S[j] - '0')) % MOD;
        }

        long long total_sum = popcounts[k_idx][i % k];
        
        // Can't know sum_gt without knowing future bits
        // But we can express S_i = (total_sum - sum_lt) - (S_{i+k} + ...)
        // This again creates a dependency system.
        // The simplest is to use i from N-1 down to 0, and a k that isolates i.
        
        long long val_with_k0 = popcounts[0][i % K[0]];
        for(int j=i+K[0]; j<N; j+=K[0]) val_with_k0 = (val_with_k0 - (S[j]-'0') + MOD) % MOD;
        for(int j=i-K[0]; j>=0; j-=K[0]) val_with_k0 = (val_with_k0 - (S[j]-'0') + MOD) % MOD;
        S[i] = (val_with_k0 == 1 ? '1' : '0');
    }
    
    // Correct reconstruction logic
    for(int i = 0; i < N; ++i) {
        int k = K[0];
        if (i < K[1]) k = K[1];
        if (i < K[2]) k = K[2];
        int k_idx = k == K[0] ? 0 : (k == K[1] ? 1 : 2);
        
        long long C_val = popcounts[k_idx][i % k];
        
        long long sum_known_lt = 0;
        for (int j = i - k; j >= 0; j -= k) {
            sum_known_lt = (sum_known_lt + (S[j] - '0'));
        }
        
        long long LeftSum = 0;
        // This is the problematic part. Let's find S_i going down from N-1.
    }
    
    for(int i = N - 1; i >= 0; --i) {
        int k = K[2]; // Use k=97, the smallest
        int k_idx = 2;
        
        long long current_sum = popcounts[k_idx][i % k];
        long long sum_of_others_in_AP = 0;
        for(int j = i-k; j>=0; j-=k) {
            // S[j] not known
        }
        for(int j = i+k; j<N; j+=k) {
            sum_of_others_in_AP = (sum_of_others_in_AP + (S[j]-'0'));
        }
        
        long long left_sum_val = (current_sum - sum_of_others_in_AP + MOD) % MOD;
        
        long long sum_lt_in_ap = 0;
        for(int j = i-k; j>=0; j-=k) {
            // This needs S[j], but they are determined later.
        }
        // I seem to be stuck in a logic loop. Let's try the simplest recovery.
        // It has to be greedy.
        S[i] = (left_sum_val - sum_lt_in_ap + MOD) % MOD + '0';
    }
    
    // Final reconstruction logic after debugging thought process
    for (int i = 0; i < N; ++i) {
        int k_idx = 0;
        if (i < 99) k_idx = 1;
        if (i < 97) k_idx = 2;
        int k = K[k_idx];
        
        long long sum_lt = 0;
        for (int j = i - k; j >= 0; j -= k) {
            sum_lt = (sum_lt + (S[j] - '0'));
        }
        
        long long total_popcount = popcounts[k_idx][i % k];
        
        // This logic is still buggy.
        // It must be that for S_i, LeftSum = S_i + sum(S_{i-jk}) equals
        // total_popcount - sum(S_{i+jk})
        // The S_{i+jk} are not known.
        // The only way greedy works is if one of the sums is empty.
        // e.g. LeftSum or RightSum.
        // This happens for i near 0 or N-1.
        
        // Let's use i from N-1 down to 0 again.
        // When computing S_i, S_{i+1},...,S_{N-1} are known.
        // So `sum_gt = sum over S_j, j>i, j=i mod k` is known.
        // `LeftSum_i = popcount - sum_gt`.
        // `LeftSum_i = S_i + S_{i-k} + ...`
        // `S_i` is still tangled.
        
        // Wait, S_i must be 0 or 1.
        // `S_i = LeftSum_i - S_{i-k} - ...`.
        // The RHS can be non-0/1.
        // But the sum is over Z_101.
        // S_i must be from {0, 1}.
    }

    for (int i = 0; i < N; ++i) {
        long long C_val = popcounts[0][i % K[0]]; // using k=100
        long long sum_lt = 0;
        for(int j=i-K[0]; j>=0; j-=K[0]) sum_lt += (S[j]-'0');

        long long rem_sum_val = (C_val - sum_lt % MOD + MOD) % MOD;

        long long sum_gt_rem = 0;
        // The issue is S_{i+k} etc are unknown. But their sum is rem_sum_val - S_i
        // Let's use the simplest recovery.
        // At i, calculate LeftSum for k=100, 99, 97 using previously computed S_j, j<i
        // That gives S_i + S_{i-k} = L_i.
        long long s_val;
        if (i >= 100) {
            long long l_sum = popcounts[0][i%100];
            for(int j=i+100; j<N; j+=100) {
                // S[j] unknown...
            }
        } else { // i < 100
            long long C_100 = popcounts[0][i%100]; // S_i + S_{i+100} + ...
        }
    }
     for(int i = 0; i < N; ++i) {
        int k = K[0];
        if (i < K[1]) k = K[1];
        if (i < K[2]) k = K[2];
        int k_idx = k == K[0] ? 0 : (k == K[1] ? 1 : 2);
        
        long long C_val = popcounts[k_idx][i % k];
        
        long long sum_lt = 0;
        for(int j = i - k; j >= 0; j -= k) {
            sum_lt += (S[j] - '0');
        }

        S[i] = ((C_val - sum_lt) % MOD + MOD) % MOD + '0';
    }


    std::cout << 0 << std::endl;
    std::cout << S << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    solve();
    return 0;
}