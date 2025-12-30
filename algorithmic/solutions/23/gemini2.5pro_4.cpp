#include <iostream>
#include <string>

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    // The Tid is irrelevant for generating the solution.
    // The solution is a fixed A=B program.
    std::cout << R"(Pa=(return)1
Pb=(return)1
Pc=(return)1
P=(return)1
PA=(return)0
PB=(return)0
PC=(return)0
PaA=P
PbB=P
PcC=P
PaB=aD
PaC=aD
PbA=bD
PbC=bD
PcA=cD
PcB=cD
Da=P
Db=P
Dc=P
S=Y
Ya=AY
Yb=BY
Yc=CY
Y=
a=Pa
b=Pb
c=Pc
)";
    return 0;
}