# created by Chirath R, chirath.02@gmail.com
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
from smtplib import SMTPException

from django.contrib.auth.models import User
from django import forms
from django.contrib.sites.shortcuts import get_current_site
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.core.mail import send_mail


from promotion.forms import JoinApplicationForm
from promotion.models import JoinApplication


approve_mail_content = ',\\n\\nWe are exited to inform that you are selected for the interview.'
reject_mail_content = ',\\n\\nWe are sorry to inform that you are not selected for the interview. Please try again ' \
                      'next time.'


class JoinApplicationListView(ListView):
    model = JoinApplication
    queryset = JoinApplication.objects.filter(is_approved=False, is_rejected=False).order_by('-date')

    def get_context_data(self, **kwargs):
        context = super(JoinApplicationListView, self).get_context_data(**kwargs)
        context['count'] = len(context['object_list'])
        return context


class JoinApplicationDetailView(DetailView):
    errors = None
    model = JoinApplication

    def get_context_data(self, **kwargs):
        context = super(JoinApplicationDetailView, self).get_context_data(**kwargs)
        context['approve_mail_subject'] = 'Congrats! FOSS@Amrita membership application'
        context['approve_mail_content'] = 'Hi ' + self.get_object().name + approve_mail_content
        context['reject_mail_subject'] = 'FOSS@Amrita membership application'
        context['reject_mail_content'] = 'Hi ' + self.get_object().name + reject_mail_content
        context['mail_error'] = self.request.GET.get('errors', None)
        return context


class JoinApplicationCreateView(CreateView):
    form_class = JoinApplicationForm
    template_name = 'base/form.html'
    success_url = reverse_lazy('join_success')

    def get_context_data(self, **kwargs):
        context = super(JoinApplicationCreateView, self).get_context_data(**kwargs)
        context['title'] = 'Applications'
        context['heading'] = 'Membership application'
        return context

    def form_valid(self, form):
        valid_form = super(JoinApplicationCreateView, self).form_valid(form)

        # generate urls
        url = ''.join(['http://', get_current_site(self.request).domain, self.get_success_url()])
        list_url = ''.join(['http://', get_current_site(self.request).domain, reverse('join_list')])

        # mail data
        subject = 'Application from ' + form.cleaned_data.get('name')
        content = 'A new application was submitted by ' + form.cleaned_data.get('name') + ' at ' + \
                  str(datetime.datetime.now()) + '. \n\nPlease visit ' + url + ' for more details. All ' \
                  'applications ' + list_url
        to_address_list = list(User.objects.filter(is_superuser=True).values_list('email', flat=True))

        # sent mail when application is submitted
        send_mail(subject, content, 'amritapurifoss@gmail.com', to_address_list, fail_silently=True)
        return valid_form


class EmailForm(forms.Form):
    mail_id = forms.EmailField()
    mail_subject = forms.CharField()
    mail_content = forms.CharField()


class JoinApplicationUpdateView(UpdateView):
    """
    Approve or reject application, sends mail to the applicant and all admin users.
    """
    model = JoinApplication
    fields = ['is_approved']

    def get(self, **kwargs):
        return HttpResponse('This view accepts only post requests')

    def post(self, request, *args, **kwargs):
        if not (request.user.is_superuser or request.user == self.get_object().created_by):
            return redirect('permission_denied')

        errors = None
        form = EmailForm(request.POST)

        if form.is_valid():
            # mail id of all the admins and the mail id from the form
            to_address_list = list(User.objects.filter(is_superuser=True).values_list('email', flat=True))
            to_address_list.append(form.cleaned_data['mail_id'])

            # sent mail, if there are errors in mail, check that too
            try:
                send_mail(form.cleaned_data['mail_subject'], form.cleaned_data['mail_content'],
                          'amritapurifoss@gmail.com', to_address_list, fail_silently=False)
                join_application = self.get_object()

                # approve
                if request.POST.get('is_approved', None):
                    join_application.is_approved = True

                # reject
                if request.POST.get('is_rejected', None):
                    join_application.is_rejected = True

                # save
                join_application.save()
            except SMTPException:
                errors = 'Mail not sent, mail id might be wrong'

            # render the detail page
            if not errors:
                return redirect(reverse('join_detail', kwargs={'pk': self.get_object().id}))
        else:
            errors = "The given mail is invalid, try again"
        # error in form
        return redirect(reverse('join_detail', kwargs={'pk': self.get_object().id}) + '?errors=' + errors)
