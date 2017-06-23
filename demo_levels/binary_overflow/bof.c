#include <stdio.h>
#include <string.h>

int main(void)
{
    char buff[15];
    int pass = 0;

    printf("Enter the password : ");
    fflush(stdout);
    gets(buff);

    if(strcmp(buff, "geek_stuff"))
    {
        printf ("\n Wrong Password \n");
    }
    else
    {
        printf ("\n Correct Password \n");
        pass = 1;
    }

    if(pass)
    {
        char* flag = "flag{geek_stuff}";
        printf("%s\n", flag);
    }

    return 0;
}